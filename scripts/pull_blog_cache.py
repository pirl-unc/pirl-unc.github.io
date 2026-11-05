#!/usr/bin/env python3
"""Download the blog cache produced by the hourly Google Cloud fetcher
(see scripts/gcp/) and apply it if it is at least as fresh as the local one.

Substack challenges GitHub-hosted runner IPs, so the feed is fetched elsewhere
and published to a public bucket. Only the expected cache files are extracted.
"""

import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = os.environ.get(
    "BLOG_CACHE_URL",
    "https://storage.googleapis.com/pirl-site-feed-galvanized-opus-161501/blog-cache.tar.gz",
)
MAX_BYTES = 200 * 1024 * 1024
ALLOWED = re.compile(r"^(data/posts\.json|data/posts_status\.json|static/assets/posts(/[A-Za-z0-9._-]+)?/?)$")


def refreshed(root):
    try:
        return json.loads((root / "data" / "posts_status.json").read_text())["last_refreshed"]
    except (OSError, ValueError, KeyError, TypeError):
        return ""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        archive = tmp / "cache.tgz"
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Cache archive is too large")
        archive.write_bytes(data)

        with tarfile.open(archive) as tar:
            members = tar.getmembers()
            for member in members:
                if not ALLOWED.match(member.name) or not (member.isfile() or member.isdir()):
                    raise ValueError(f"Unexpected path in cache archive: {member.name}")
            extracted = tmp / "x"
            extracted.mkdir()
            tar.extractall(extracted, members=members, filter="data")

        posts = json.loads((extracted / "data" / "posts.json").read_text(encoding="utf-8"))
        if not (isinstance(posts, list) and posts and all(p.get("title") and p.get("url") for p in posts)):
            raise ValueError("Cache archive has no valid posts")
        if refreshed(extracted) < refreshed(ROOT):
            print("Remote cache is older than the local one; keeping local")
            return 0

        shutil.copy(extracted / "data" / "posts.json", ROOT / "data" / "posts.json")
        status = extracted / "data" / "posts_status.json"
        if status.exists():
            shutil.copy(status, ROOT / "data" / "posts_status.json")
        covers = extracted / "static" / "assets" / "posts"
        if covers.is_dir():
            target = ROOT / "static" / "assets" / "posts"
            target.mkdir(parents=True, exist_ok=True)
            for cover in covers.iterdir():
                shutil.copy(cover, target / cover.name)
        print(f"Applied Google Cloud blog cache ({len(posts)} posts, refreshed {refreshed(extracted)})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::Could not apply Google Cloud blog cache: {exc}")
        sys.exit(1)
