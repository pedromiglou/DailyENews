import logging
import re
import urllib.parse
from functools import lru_cache, cached_property

from goose3 import Goose
from lxml import etree
from jarr.bootstrap import conf
from jarr.controllers.article import to_vector
from jarr.lib.enums import ArticleType, FeedType
from jarr.lib.url_cleaners import remove_utm_tags
from jarr.lib.utils import clean_lang, digest

logger = logging.getLogger(__name__)
IMG_ALT_MAX_LENGTH = 100
# From : https://gist.github.com/TrevorJTClarke/a14c37db3c11ee23a700
SCHEME = re.compile(r'^(?:https?:\/\/)')
YOUTUBE_RE = re.compile(
    r'^(?:https?:\/\/)?(?:i\.|www\.|img\.)?(?:youtu\.be\/|youtube\.com\/|ytim'
    r'g\.com\/)(?:embed\/|v\/|vi\/|vi_webp\/|watch\?v=|watch\?.+&v=)((\w|-){'
    r'11})(?:\S+)?$')
VIMEO_RE = re.compile(
    r'https?:\/\/(?:vimeo\.com\/|player\.vimeo\.com\/)(?:video\/|(?:channels'
    r'\/staffpicks\/|channels\/)|)((\w|-){7,9})')
SPOTIFY_RE = re.compile(
    r'https?:\/\/(?:embed\.|open\.)(?:spotify\.com\/)(?:playlist\/|track\/|\?uri=spotif'
    r'y:track:)((\w|-){22})')
SOUNDCLOUD_RE = re.compile(
    r'https?:\/\/(?:w\.|www\.|)(?:soundcloud\.com\/)(?:(?:player\/\?url=http'
    r's\%3A\/\/api.soundcloud.com\/tracks\/)|)(((\w|-)[^A-z]{7})|([A-Za-z0-9'
    r']+(?:[-_][A-Za-z0-9]+)*(?!\/sets(?:\/|$))(?:\/[A-Za-z0-9]+(?:[-_][A-Za'
    r'-z0-9]+)*){1,2}))')
EMBEDDED_RE = ((YOUTUBE_RE, 'youtube'),
               (VIMEO_RE, 'vimeo'),
               (SPOTIFY_RE, 'spotify'),
               (SOUNDCLOUD_RE, 'soundcloud'))


class EmbeddedLinkParser:
    _types = (('youtube', ('youtube.com', 'youtu.be')),
              ('vimeo', ('vimeo.com',)),
              ('spotify', ('spotify.com',)),
              ('soundcloud', ('soundcloud.com',)))

    def __init__(self, link):
        self._split = None
        self._link = link
        if not SCHEME.match(self._link):
            self._link = f"https://{self._link.lstrip('htps:/')}"
        if SCHEME.match(self._link):
            self._split = urllib.parse.urlsplit(self._link)
            if self._split and (not self._split.netloc
                                or not self._split.path):
                self._split = None

    @cached_property
    def type(self):
        for type_, domains in self._types:
            for domain in domains:
                if self._split.netloc.endswith(domain):
                    return type_
        print('no type')

    @cached_property
    def _qs(self):
        return urllib.parse.parse_qs(self._split.query)

    def qs_has(self, key):
        return bool(self._qs.get(key))

    @cached_property
    def sub_type(self):
        split_path = self._split.path
        if self.type == 'youtube':
            for path in 'watch', 'embed', 'vi_webp', 'v':
                if split_path.startswith(f"/{path}") and self._qs.get('v'):
                    return 'video'
            if split_path.startswith('/playlist') and self._qs.get('list'):
                return 'playlist'

    @cached_property
    def embedded_id(self):
        if self.type == 'youtube' and self.sub_type == 'video':
            return self._qs['v'][0]
        if self.type == 'youtube' and self.sub_type == 'playlist':
            return self._qs['list'][0]
        if self.type == 'soundcloud' and self.sub_type == 'track':
            return self._split.path
        if self.type == 'soundcloud' and self.sub_type == 'playlist':
            return
        if self.type == 'spotify':
            return self._split.path.strip('/').split('/')[1]
        if self.type == 'vimeo':
            return self._split.path.strip('/')

        raise ValueError(f'no embedded id for {self._link}')

    @property
    def embedded_hash(self):
        return digest(f'emb:{self.type}:{self.sub_type}:{self.embedded_id}',
                      alg='sha1', out='bytes')


@lru_cache(maxsize=10000)
def get_embedded_link_parser(link):
    return EmbeddedLinkParser(link)


class ContentGenerator:
    article_type = None
    feed_type = None

    def __init__(self, article):
        self.article = article
        self._page = None
        self.extracted_infos = {}

    def _get_goose(self):
        goose = Goose({"browser_user_agent": conf.crawler.user_agent})
        try:
            self._page = goose.extract(self.article.link)
        except Exception as error:
            logger.error("something wrong happened while trying to fetch "
                         "%r: %r", self.article.link, error)
        if not self._page:
            return False
        lang = self._page.opengraph.get('locale') or self._page.meta_lang
        self.extracted_infos['lang'] = clean_lang(lang)
        self.extracted_infos['link'] = self._page.final_url
        keywords = set(self._page.meta_keywords.split(', '))
        self.extracted_infos['tags'] = set(self._page.tags).union(keywords)
        self.extracted_infos['title'] = self._page.title
        return True

    def get_vector(self):
        if self._page is None:
            self._get_goose()
        if self._page and self.extracted_infos:
            return to_vector(self.extracted_infos, self._page)

    def _from_goose_to_html(self, encoding="utf8"):
        result = ""
        current_node = self._page.top_node
        while True:
            result += etree.tostring(current_node,
                                     encoding=encoding).decode(encoding)
            current_node = current_node.getnext()
            if current_node is None:
                break
        return result

    @staticmethod
    def generate():
        return {}

    def generate_and_merge(self, content):
        content = migrate_content(content)
        # if there is already some fetched content
        already_fetched = any(cnt.get('type') == 'fetched'
                              for cnt in content.get('contents') or [])
        if isinstance(self, TruncatedContentGenerator) and already_fetched:
            return content
        article_content = self.generate()
        if not article_content:
            return content
        content['contents'].append(article_content)
        return content


class MediaContentGenerator(ContentGenerator):

    @staticmethod
    def get_vector():
        return None

    @staticmethod
    def generate():
        return {}

    @staticmethod
    def generate_and_merge(content):
        return content


class ImageContentGenerator(MediaContentGenerator):
    article_type = ArticleType.image


class AudioContentGenerator(MediaContentGenerator):
    article_type = ArticleType.audio


class VideoContentGenerator(MediaContentGenerator):
    article_type = ArticleType.video


class EmbeddedContentGenerator(ContentGenerator):
    article_type = ArticleType.embedded

    @staticmethod
    def get_vector():
        return None

    def generate(self):
        parser = EmbeddedLinkParser(self.article.link)
        if parser:
            logger.info('%r constructing embedded %s content '
                        'from article', self.article, parser.type)
            try:
                return {'type': parser.type, 'link': parser.embedded_id}
            except ValueError:
                pass
        else:
            logger.warning('embedded video not recognized %r',
                           self.article.link)
        return {}


class TruncatedContentGenerator(ContentGenerator):

    def generate(self):
        if self._page is None:
            self._get_goose()
        content = {'type': 'fetched'}
        try:
            content['content'] = self._from_goose_to_html()
            content['link'] = remove_utm_tags(self._page.final_url)
            content['title'] = self._page.title
        except Exception:
            logger.exception("Could not rebuild parsed content for %r",
                             self.article)
            return {}
        if self.article.comments:
            content['comments'] = self.article.comments
        logger.debug('%r no special type found doing nothing', self.article)
        return content


class RedditContentGenerator(TruncatedContentGenerator):
    feed_type = FeedType.reddit

    def __init__(self, article):
        self._is_pure_reddit_post = None
        super().__init__(article)

    @property
    def is_pure_reddit_post(self):
        if self._is_pure_reddit_post is not None:
            return self._is_pure_reddit_post  # no re-computing
        self._is_pure_reddit_post = False
        if self.article.article_type is not None:
            return self._is_pure_reddit_post
        try:
            split = urllib.parse.urlsplit(self.article.link)
            paths = split.path.strip('/').split('/')
            if ('reddit.com' in split.netloc
                    and paths[0] == 'r' and paths[2] == 'comments'):
                self._is_pure_reddit_post = True
        except (AttributeError, IndexError):
            pass
        return self._is_pure_reddit_post

    def get_vector(self):
        if not self.is_pure_reddit_post:
            return super().get_vector()

    def generate(self):
        if not self.is_pure_reddit_post:
            return super().generate()
        return {}  # original reddit post, nothing to process


CONTENT_GENERATORS = {}


def feed_mapping(subcls_):
    if subcls_.feed_type is not None:
        CONTENT_GENERATORS[subcls_.feed_type] = subcls_
    if subcls_.article_type is not None:
        CONTENT_GENERATORS[subcls_.article_type] = subcls_


for subcls in ContentGenerator.__subclasses__():
    feed_mapping(subcls)
    for subsubcls in subcls.__subclasses__():
        feed_mapping(subsubcls)


@lru_cache()
def get_content_generator(article):
    if article.article_type and article.article_type in CONTENT_GENERATORS:
        return CONTENT_GENERATORS[article.article_type](article)

    if article.feed.feed_type \
            and article.feed.feed_type in CONTENT_GENERATORS:
        return CONTENT_GENERATORS[article.feed.feed_type](article)

    if article.feed.truncated_content:
        return TruncatedContentGenerator(article)

    return ContentGenerator(article)


def migrate_content(content: dict):
    content = content or {'v': 2, 'contents': []}
    if content.get('v') == 2:
        return content
    if content['type'] in {'image', 'audio', 'video'}:
        return {'v': 2, 'contents': []}
    if content['type'] == 'embedded':  # migrating original embedded
        return {'v': 2, 'contents': [{'type': content['player'],
                                      'link': content['videoId']}]}
    return {'v': 2, 'contents': [content]}
