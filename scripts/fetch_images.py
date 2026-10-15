#!/usr/bin/env python3
"""One-time migration helper: download every image still hosted on Squarespace
into static/assets/ so the site keeps working after the Squarespace plan ends.

    python scripts/fetch_images.py

Safe to re-run; existing files are skipped. Commit the downloaded files.
"""

import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"


def download(url: str, dest: Path) -> bool:
    if dest.exists():
        print(f"  skip   {dest.relative_to(ROOT)} (exists)")
        return True
    # Ask Squarespace for a reasonably sized rendition rather than the original.
    parts = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parts.query))
    query.setdefault("format", "1000w")
    url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 pirl-site-migration"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001
        print(f"  FAILED {dest.relative_to(ROOT)}: {exc}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"  saved  {dest.relative_to(ROOT)} ({len(data) // 1024} KB)")
    return True


def main() -> int:
    ok = True
    site = yaml.safe_load((ROOT / "data" / "site.yml").read_text())
    print("Site images")
    for img in site["images"].values():
        ok &= download(img["remote"], STATIC / img["local"])

    people = yaml.safe_load((ROOT / "data" / "people.yml").read_text())
    print("People photos")
    for group in people["groups"]:
        for person in group["people"]:
            if person.get("photo_url") and person.get("photo"):
                ok &= download(person["photo_url"], STATIC / "assets" / "people" / person["photo"])

    if not ok:
        print("\nSome downloads failed. Re-run, or save those images by hand.")
        return 1
    print("\nDone. Commit static/assets/ and the site will stop depending on Squarespace.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
