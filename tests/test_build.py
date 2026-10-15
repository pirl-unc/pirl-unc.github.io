import contextlib
import copy
import io
import os
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import build


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class BuildTests(unittest.TestCase):
    def render(self, url):
        with patch.dict(os.environ, {'SITE_URL': url}), patch.object(build, 'OUT', build.ROOT / '_site'), contextlib.redirect_stdout(io.StringIO()):
            build.main()
        return build.ROOT / '_site'

    def test_root_and_github_project_links_and_covers(self):
        for prefix in ['', '/pirl-site']:
            with self.subTest(prefix=prefix):
                out = self.render('https://example.org' + prefix)
                for page in out.rglob('*.html'):
                    for tag, attrs in Elements(page.read_text()).elements:
                        for key in ['src', 'href', 'srcset']:
                            value = attrs.get(key, '')
                            if not value.startswith('/') or value.startswith('//'):
                                continue
                            self.assertTrue(value.startswith(prefix + '/'), value)
                            target = out / urlsplit(value)[2][len(prefix):].lstrip('/')
                            self.assertTrue(target.exists(), f'{page.name}: {value}')
                home = (out / 'index.html').read_text()
                recent = build.load_json('posts.json', [])[:build.load_yaml('site.yml').get('recent_posts', 6)]
                self.assertEqual(home.count('class="post"'), len(recent))
                local_covers = [attrs['src'] for tag, attrs in Elements(home).elements if tag == 'img' and '/assets/posts/' in attrs.get('src', '')]
                expected_covers = sum(bool(post.get('image_local')) and (build.STATIC / post['image_local']).is_file() for post in recent)
                self.assertEqual(len(local_covers), expected_covers)
                self.assertIn('https://example.org' + prefix + '/', home)
                redirect = (out / 'research/index.html').read_text()
                self.assertIn(f'url={prefix}/papers/', redirect)

    def test_reordering_contacts_keeps_portraits_with_people(self):
        original_load = build.load_yaml
        contact = copy.deepcopy(original_load('contact.yml'))
        contact['sections'].reverse()
        contact['investigators']['contacts'].reverse()
        def reordered(name):
            return contact if name == 'contact.yml' else original_load(name)
        with patch.object(build, 'load_yaml', side_effect=reordered):
            out = self.render('https://example.org')
        html = (out / 'contact/index.html').read_text()
        images = {attrs.get('alt'): attrs.get('src') for tag, attrs in Elements(html).elements if tag == 'img'}
        for person in contact['investigators']['contacts']:
            self.assertEqual(images[person['name']], '/' + person['image'])

    def test_reordering_people_keeps_layouts(self):
        original_load = build.load_yaml
        people = copy.deepcopy(original_load('people.yml'))
        people['groups'].reverse()
        def reordered(name):
            return people if name == 'people.yml' else original_load(name)
        with patch.object(build, 'load_yaml', side_effect=reordered):
            out = self.render('https://example.org')
        html = (out / 'people/index.html').read_text()
        sections = [attrs['class'] for tag, attrs in Elements(html).elements if tag == 'section']
        self.assertEqual(sections[0], 'people-group people-group-alumni')
        self.assertEqual(sections[-1], 'people-group people-group-investigators')

    def test_build_cannot_delete_source_or_arbitrary_directory(self):
        for path in [build.ROOT, build.DATA, Path('/tmp/other-project')]:
            with self.subTest(path=path), patch.object(build, 'OUT', path):
                with self.assertRaises(ValueError):
                    build.main()


if __name__ == '__main__':
    unittest.main()
