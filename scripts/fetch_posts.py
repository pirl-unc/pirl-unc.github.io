#!/usr/bin/env python3
"""Refresh Substack posts and cache their covers for static hosting.

An unavailable feed retains a valid cache. A failed first import exits nonzero.
Use --cached-only to download covers for an existing post cache without RSS.
"""

import argparse
import hashlib
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "posts.json"
STATIC = ROOT / "static"
MAX_POSTS = 20
MAX_BYTES = 12 * 1024 * 1024
NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
}


def web_url(value, base=""):
    url = urljoin(base, value or "") if value else ""
    return url if urlsplit(url).scheme in {"http", "https"} else ""


def fetch(url):
    if not web_url(url):
        raise ValueError("Expected an HTTP(S) URL")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; pirl-site-builder/1.0; +https://pirl.unc.edu)",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Response exceeds 12 MB")
    return data


class FeedHTML(HTMLParser):
    """Extract text and content images without rendering feed HTML."""

    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.words = []
        self.images = []
        self.ignored = 0
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.ignored += 1
        if self.ignored:
            return
        if tag in {"p", "br", "div", "li"}:
            self.words.append(" ")
        if tag == "img":
            # Do not use tracking pixels as post covers.
            if attrs.get("width") not in {"0", "1"} and attrs.get("height") not in {"0", "1"}:
                self.images.append(attrs.get("src") or attrs.get("data-src") or "")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored = max(0, self.ignored - 1)
        elif tag in {"p", "div", "li"}:
            self.words.append(" ")

    def handle_data(self, data):
        if not self.ignored:
            self.words.append(data)

    @property
    def plain_text(self):
        return " ".join("".join(self.words).split())


def text(element, tag):
    return (element.findtext(tag, default="", namespaces=NS) or "").strip()


def excerpt(value, max_words=60):
    """Keep feed previews short and end at a word boundary."""
    words = value.split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        raise ValueError(f"Expected RSS, received <{root.tag}>")
    posts = []
    for item in channel.findall("item"):
        title, link = text(item, "title"), web_url(text(item, "link"))
        if not title or not link:
            continue
        description = FeedHTML(text(item, "description"))
        content = FeedHTML(text(item, "content:encoded"))
        candidates = []
        for enclosure in item.findall("enclosure"):
            if enclosure.get("type", "").startswith("image/"):
                candidates.append(enclosure.get("url"))
        for media in item.findall(".//media:content", NS):
            if media.get("medium") == "image" or media.get("type", "").startswith("image/"):
                candidates.append(media.get("url"))
        candidates.extend(node.get("url") for node in item.findall(".//media:thumbnail", NS))
        candidates.extend(content.images + description.images)
        image = next((web_url(url, link) for url in candidates if web_url(url, link)), "")
        date_iso = ""
        try:
            date_iso = parsedate_to_datetime(text(item, "pubDate")).date().isoformat()
        except (TypeError, ValueError, AttributeError, OverflowError):
            pass
        posts.append({
            "title": title, "subtitle": description.plain_text[:400],
            "url": link, "date": date_iso, "author": text(item, "dc:creator"),
            "image": image,
            "excerpt": excerpt(content.plain_text or description.plain_text),
        })
    posts.sort(key=lambda post: post["date"], reverse=True)
    return posts[:MAX_POSTS]


def image_extension(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data[:6] in {b"GIF87a", b"GIF89a"}:
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Cover response is not a supported image")


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def cache_images(posts, previous):
    old_by_url = {post["url"]: post for post in previous}
    for post in posts:
        old = old_by_url.get(post["url"], {})
        post["image"] = post.get("image") or old.get("image", "")
        old_local = old.get("image_local", "")
        if old_local and (STATIC / old_local).is_file():
            post["image_local"] = old_local
            post["image_cached_url"] = old.get("image_cached_url", old.get("image", ""))
            if post["image"] == post["image_cached_url"]:
                continue
        if not post["image"]:
            continue
        try:
            data = fetch(post["image"])
            name = hashlib.sha256(post["image"].encode()).hexdigest()[:20] + image_extension(data)
            local = "assets/posts/" + name
            atomic_write(STATIC / local, data)
            post["image_local"] = local
            post["image_cached_url"] = post["image"]
        except Exception as exc:
            print(f"::warning::Cover unavailable for {post['title']}: {exc}")


def read_cache():
    try:
        posts = json.loads(OUT.read_text(encoding="utf-8"))
        if isinstance(posts, list) and posts and all(
            isinstance(post, dict) and post.get("title") and web_url(post.get("url"))
            for post in posts
        ):
            return posts
    except (OSError, ValueError, TypeError):
        pass
    return []


def main(cached_only=False):
    previous = read_cache()
    if cached_only:
        posts = previous
    else:
        site = yaml.safe_load((ROOT / "data" / "site.yml").read_text(encoding="utf-8"))
        try:
            posts = parse(fetch(site["blog_feed"]))
            if not posts:
                raise ValueError("Feed contains no usable posts")
        except Exception as exc:
            print(f"::warning::Could not refresh RSS: {exc}")
            print("Keeping cached posts" if previous else "No valid post cache; import failed")
            return 0 if previous else 1
    if not posts:
        return 1
    previous_by_url = {post["url"]: post for post in previous}
    for post in posts:
        if not post.get("excerpt"):
            post["excerpt"] = previous_by_url.get(post["url"], {}).get("excerpt", "")
    cache_images(posts, previous)
    atomic_write(OUT, (json.dumps(posts, indent=2, ensure_ascii=False) + "\n").encode())
    print(f"Saved {len(posts)} posts, {sum(bool(p.get('image_local')) for p in posts)} local covers")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached-only", action="store_true")
    sys.exit(main(parser.parse_args().cached_only))
