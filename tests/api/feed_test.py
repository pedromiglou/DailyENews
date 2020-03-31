from tests.base import JarrFlaskCommon
from datetime import timezone, timedelta
from jarr.lib.utils import utc_now
from jarr.lib.enums import FeedType
from jarr.controllers import FeedController
from jarr.crawler.main import feed_cleaner


FEED = {'link': 'https://1pxsolidblack.pl/feeds/all.atom.xml',
        'site_link': 'https://1pxsolidblack.pl/',
        'title': '1pxsolidblack',
        'icon_url': 'https://1pxsolidblack.pl/img/favicon.ico'}


class FeedApiTest(JarrFlaskCommon):

    def _get(self, id_, user):
        return next(feed for feed in self.jarr_client('get', 'feeds',
                    user='user1').json if feed['id'] == id_)

    def test_NewFeedResource_post(self):
        cats = self.jarr_client('get', 'categories', user='user1').json
        other_cats = self.jarr_client('get', 'categories', user='user2').json

        resp = self.jarr_client('post', 'feed',
                data={'title': 'my new feed'})
        self.assertStatusCode(401, resp)

        resp = self.jarr_client('post', 'feed',
                data={'title': 'my new feed'}, user='user1')
        self.assertStatusCode(400, resp)

        resp = self.jarr_client('post', 'feed',
                data={'title': 'my new feed', 'link': 'my link'}, user='user1')
        self.assertStatusCode(201, resp)

        resp = self.jarr_client('post', 'feed',
                data={'title': 'my new feed',
                      'link': 'my link', 'category_id': cats[0]['id']},
                user='user1')
        self.assertStatusCode(201, resp)

        resp = self.jarr_client('post', 'feed',
                data={'title': 'my new feed',
                      'link': 'my link', 'category_id': other_cats[0]['id']},
                user='user1')
        self.assertStatusCode(403, resp)

        feeds = self.jarr_client('get', 'feeds', user='user1').json
        self.assertEqual(1, len([feed for feed in feeds
                                 if feed['title'] == 'my new feed'
                                     and feed['category_id'] is None]))
        self.assertEqual(1, len([feed for feed in feeds
                                 if feed['title'] == 'my new feed'
                                    and feed['category_id'] == cats[0]['id']]))

    def test_ListFeedResource_get(self):
        resp = self.jarr_client('get', 'feeds')
        self.assertStatusCode(401, resp)
        feeds_u1 = self.jarr_client('get', 'feeds', user='user1').json
        feeds_u2 = self.jarr_client('get', 'feeds', user='user2').json
        feeds_u1 = [f['id'] for f in feeds_u1]
        feeds_u2 = [f['id'] for f in feeds_u2]

        self.assertFalse(set(feeds_u1).intersection(feeds_u2))

        # testing time formating
        feed = self.jarr_client('get', 'feeds', user='user1').json[0]
        now = utc_now()
        FeedController().update({'id': feed['id']}, {'last_retrieved': now})
        json = self._get(feed['id'], 'user1')
        self.assertEqual(json['last_retrieved'], now.isoformat())

        FeedController().update({'id': feed['id']},
                {'last_retrieved': now.replace(tzinfo=None)})
        json = self._get(feed['id'], 'user1')
        self.assertEqual(json['last_retrieved'], now.isoformat())

        FeedController().update({'id': feed['id']},
                {'last_retrieved':
                    now.astimezone(timezone(timedelta(hours=12)))})
        json = self._get(feed['id'], 'user1')
        self.assertEqual(json['last_retrieved'], now.isoformat())

    def test_FeedResource_put(self):
        resp = self.jarr_client('put', 'feed', 1)
        self.assertStatusCode(401, resp)
        feeds_resp = self.jarr_client('get', 'feeds', user='user1')
        self.assertStatusCode(200, feeds_resp)
        existing_feed = feeds_resp.json[0]
        categories_resp = self.jarr_client('get', 'categories', user='user2')
        self.assertStatusCode(200, categories_resp)
        category = categories_resp.json[0]
        resp = self.jarr_client('put', 'feed', existing_feed['id'],
                data={'title': 'changed'})
        self.assertStatusCode(401, resp)
        resp = self.jarr_client('put', 'feed', existing_feed['id'],
                data={'title': 'changed'}, user='user2')
        self.assertStatusCode(403, resp)
        resp = self.jarr_client('put', 'feed', existing_feed['id'],
                data={'title': 'changed'}, user='user1')
        self.assertStatusCode(204, resp)
        resp = self.jarr_client('put', 'feed', existing_feed['id'],
                data={'category_id': category['id']}, user='user1')
        self.assertStatusCode(403, resp)

    def test_FeedResource_delete(self):
        feed_id = self.jarr_client('get', 'feeds', user='user1').json[0]['id']
        resp = self.jarr_client('delete', 'feed', feed_id)
        self.assertStatusCode(401, resp)
        resp = self.jarr_client('delete', 'feed', feed_id, user='user2')
        self.assertStatusCode(403, resp)

        resp = self.jarr_client('get', 'list-feeds', user='user1')
        self.assertTrue(feed_id in {row['fid'] for row in resp.json})

        resp = self.jarr_client('delete', 'feed', feed_id, user='user1')
        self.assertStatusCode(204, resp)

        resp = self.jarr_client('get', 'list-feeds', user='user1')
        self.assertFalse(feed_id in {row['fid'] for row in resp.json})

        feeds = self.jarr_client('get', 'feeds', user='user1').json
        self.assertTrue(feed_id in [feed['id'] for feed in feeds])
        self.assertEqual('to_delete', [feed['status'] for feed in feeds
                                       if feed['id'] == feed_id][0])
        feed_cleaner()

        feeds = self.jarr_client('get', 'feeds', user='user1').json
        self.assertFalse(feed_id in [feed['id'] for feed in feeds])

        resp = self.jarr_client('get', 'list-feeds', user='user1')
        self.assertFalse(feed_id in {row['fid'] for row in resp.json})

    def test_FeedBuilder_get(self):
        resp = self.jarr_client('get', 'feed', 'build')
        self.assertStatusCode(401, resp)

        resp = self.jarr_client('get', 'feed', 'build', user='user1')
        self.assertStatusCode(400, resp)

        resp = self.jarr_client('get', 'feed', 'build', user='user1',
                                data={'url': "koreus.com"})
        self.assertStatusCode(200, resp)
        self.assertEqual({
            'description': 'Koreus',
            'feed_type': FeedType.koreus.value,
            'icon_url': 'https://koreus.cdn.li/static/images/favicon.png',
            'link': 'http://feeds.feedburner.com/Koreus-articles',
            'links': ['http://feeds.feedburner.com/Koreus-articles',
                      'http://feeds.feedburner.com/Koreus-media',
                      'http://feeds.feedburner.com/Koreus-videos',
                      'http://feeds.feedburner.com/Koreus-animations',
                      'http://feeds.feedburner.com/Koreus-jeux',
                      'http://feeds.feedburner.com/Koreus-images',
                      'http://feeds.feedburner.com/Koreus-sons',
                      'http://feeds.feedburner.com/Koreus-podcasts-audio',
                      'http://feeds.feedburner.com/Koreus-podcasts-video',
                      'http://feeds.feedburner.com/Koreus-forums'],
            'site_link': 'https://www.koreus.com/',
            'title': 'Koreus.com - Articles'}, resp.json)

    def test_IconResource_get(self):
        resp = self.jarr_client('post', 'feed', user='user1', data=FEED)
        self.assertStatusCode(201, resp)
        feed = resp.json
        resp = self.jarr_client('get', 'feed', 'icon',
                                data={'url': feed['icon_url']})
        self.assertStatusCode(200, resp)
        self.assertTrue(resp.headers['Content-Type'].startswith('image/'))