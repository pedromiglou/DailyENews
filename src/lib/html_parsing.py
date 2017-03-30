from functools import lru_cache

from bs4 import BeautifulSoup, SoupStrainer

from lib.const import FEED_MIMETYPES
from lib.utils import jarr_get, rebuild_url

CHARSET_TAG = b'<meta charset='


def try_get_icon_url(url, *splits):
    for split in splits:
        if split is None:
            continue
        rb_url = rebuild_url(url, split)
        response = None
        # if html in content-type, we assume it's a fancy 404 page
        try:
            response = jarr_get(rb_url)
            content_type = response.headers.get('content-type', '')
        except Exception:
            pass
        else:
            if response is not None and response.ok \
                    and 'html' not in content_type and response.content:
                return response.url
    return None


def _meta_w_charset(elem):
    return elem.name == 'meta' and 'charset' in elem.attrs


def _extract_charset(content, strainer):
    parsed = BeautifulSoup(content, 'html.parser', parse_only=strainer)
    for meta in parsed.find_all(_meta_w_charset):
        return meta.attrs['charset']


def _try_encodings(content, *encodings):
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except Exception:
            pass
    return content.decode('utf8', 'ignore')


@lru_cache(maxsize=None)
def get_soup(content, header_encoding='utf8'):
    """For a content and an encoding will return a bs4 object which will be
    cached so you can call on this method as often as you want.

    As the encoding written in the HTML is more reliable, ```get_soup``` will
    try this one before parsing with the one in args.
    """
    strainer = SoupStrainer('head')
    decoded_content = None
    if not isinstance(content, str):
        encodings = [_extract_charset(content, strainer), header_encoding] \
                if CHARSET_TAG in content else [header_encoding]
        decoded_content = _try_encodings(content, encodings)
    for cnt in decoded_content, content:
        if cnt:
            try:
                return BeautifulSoup(cnt, 'html.parser', parse_only=strainer)
            except Exception as error:
                logger.warn('something went wrong when parsing: %r', error)


def extract_title(response, og_prop='og;title'):
    """From a requests.Response objects will return the title."""
    soup = get_soup(response.content, response.encoding)
    try:
        return soup.find_all('meta', property=og_prop)[0].attrs['content']
    except Exception:
        try:
            return soup.find_all('title')[0].text
        except Exception:
            pass


def extract_tags(response):
    """From a requests.Response objects will return the tags
    (keywords + open graphs ones)."""
    soup = get_soup(response.content, response.encoding)
    if not soup:
        return {}
    tags = set()
    keywords = soup.find_all('meta', {'name': 'keywords'})
    if keywords:
        tags = set(sum([keyword.attrs.get('content', '').split(',')
                        for keyword in keywords], []))
    tags = tags.union({meta.attrs.get('content', '')
                       for meta in soup.find_all('meta',
                                                 {'property': 'article:tag'})})
    return {tag.lower().strip() for tag in tags if tag.strip()}


def _check_keys(**kwargs):
    """Returns a callable for BeautifulSoup.find_all add will check existence
    of key and values they hold in the in listed elements.
    """
    def wrapper(elem):
        for key, vals in kwargs.items():
            if not elem.has_attr(key):
                return False
            if not all(val in elem.attrs[key] for val in vals):
                return False
        return True
    return wrapper


def extract_icon_url(response, site_split, feed_split):
    soup = get_soup(response.content, response.encoding)
    if not soup:
        return
    icons = soup.find_all(_check_keys(rel=['icon', 'shortcut']))
    if not len(icons):
        icons = soup.find_all(_check_keys(rel=['icon']))
    if len(icons) >= 1:
        for icon in icons:
            icon_url = try_get_icon_url(icon.attrs['href'],
                                        site_split, feed_split)
            if icon_url:
                return icon_url

    icon_url = try_get_icon_url('/favicon.ico', site_split, feed_split)
    if icon_url:
        return icon_url


def extract_feed_link(response, feed_split):
    soup = get_soup(response.content, response.encoding)
    for tpe in FEED_MIMETYPES:
        alternates = soup.find_all(_check_keys(rel=['alternate'], type=[tpe]))
        if len(alternates) >= 1:
            return rebuild_url(alternates[0].attrs['href'], feed_split)