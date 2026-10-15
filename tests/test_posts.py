import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import fetch_posts as feed


def rss(extra=""):
    return f'''<rss xmlns:media="{feed.NS['media']}" xmlns:content="{feed.NS['content']}">
    <channel><item><title>Example</title><link>https://example.org/post</link>
    <pubDate>Fri, 17 Oct 2025 10:00:00 GMT</pubDate>{extra}</item></channel></rss>'''.encode()


class FeedTests(unittest.TestCase):
    def test_image_sources(self):
        sources = [
            '<enclosure type="image/jpeg" url="https://example.org/cover.jpg"/>',
            '<media:content medium="image" url="https://example.org/cover.jpg"/>',
            '<media:thumbnail url="https://example.org/cover.jpg"/>',
            '<content:encoded><![CDATA[<img src="/cover.jpg">]]></content:encoded>',
            '<description><![CDATA[<img data-src="/cover.jpg">]]></description>',
        ]
        for source in sources:
            with self.subTest(source=source):
                post = feed.parse(rss(source))[0]
                self.assertEqual(post['image'], 'https://example.org/cover.jpg')
                self.assertEqual(post['date'], '2025-10-17')

    def test_audio_tracking_pixels_and_unsafe_urls_are_not_covers(self):
        source = '''<enclosure type="audio/mpeg" url="https://example.org/audio.mp3"/>
        <description><![CDATA[<img src="/pixel" width="1"><img src="javascript:alert(1)">
        <img src="/cover.jpg">]]></description>'''
        self.assertEqual(feed.parse(rss(source))[0]['image'], 'https://example.org/cover.jpg')

    def test_description_is_plain_text(self):
        source = '<description><![CDATA[<p>One <b>bold</b> &amp; two.</p><p>Next.</p><script>bad()</script>]]></description>'
        self.assertEqual(feed.parse(rss(source))[0]['subtitle'], 'One bold & two. Next.')

    def test_html_error_page_is_not_a_feed(self):
        with self.assertRaises(ValueError):
            feed.parse(b'<html><body>Site Unavailable</body></html>')

    def test_failed_refresh_preserves_cache_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'posts.json'
            original = json.dumps(feed.parse(rss())).encode()
            path.write_bytes(original)
            with patch.object(feed, 'OUT', path), patch.object(feed, 'fetch', side_effect=OSError('offline')):
                self.assertEqual(feed.main(), 0)
                self.assertEqual(path.read_bytes(), original)

    def test_failed_first_import_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(feed, 'OUT', Path(directory) / 'posts.json'), patch.object(feed, 'fetch', return_value=b'<html/>'):
                self.assertEqual(feed.main(), 1)

    def test_cover_cache_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = feed.parse(rss('<enclosure type="image/png" url="https://example.org/a.png"/>'))
            with patch.object(feed, 'STATIC', Path(directory)), patch.object(feed, 'fetch', return_value=b'\x89PNG\r\n\x1a\nexample') as fetch:
                feed.cache_images(previous, [])
                new = feed.parse(rss())
                feed.cache_images(new, previous)
                self.assertEqual(fetch.call_count, 1)
                self.assertEqual(new[0]['image_local'], previous[0]['image_local'])
                self.assertTrue((Path(directory) / new[0]['image_local']).is_file())

    def test_changed_cover_failure_keeps_old_cover_and_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            static = Path(directory)
            (static / 'old.png').write_bytes(b'old image')
            previous = feed.parse(rss())
            previous[0].update(image='https://example.org/old.png', image_local='old.png')
            new = copy.deepcopy(previous)
            new[0]['image'] = 'https://example.org/new.png'
            with patch.object(feed, 'STATIC', static), patch.object(feed, 'fetch', return_value=b'<html>Unavailable</html>') as fetch:
                feed.cache_images(new, previous)
                retry = copy.deepcopy(new)
                feed.cache_images(retry, new)
                self.assertEqual(fetch.call_count, 2)
                self.assertEqual(retry[0]['image_local'], 'old.png')
                self.assertEqual((static / 'old.png').read_bytes(), b'old image')


if __name__ == '__main__':
    unittest.main()
