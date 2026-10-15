#!/usr/bin/env python3
"""Fetch public repositories of the GitHub org and write data/repos.json.

Uses GH_TOKEN / GITHUB_TOKEN when present (the Action provides one) for the
authenticated API rate limit. On failure the existing cache is kept.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "repos.json"


def fetch_json(url: str, token: str | None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pirl-site-builder/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main() -> int:
    site = yaml.safe_load((ROOT / "data" / "site.yml").read_text())
    org = site["github_org"]
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    repos = []
    page = 1
    try:
        while True:
            batch = fetch_json(
                f"https://api.github.com/orgs/{org}/repos?type=public&per_page=100&page={page}",
                token,
            )
            if not batch:
                break
            repos.extend(batch)
            page += 1
            if page > 10:
                break
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::Could not refresh repos for {org}: {exc}")
        print("Keeping existing data/repos.json")
        return 0

    cleaned = [
        {
            "name": r["name"],
            "description": r.get("description") or "",
            "url": r["html_url"],
            "language": r.get("language") or "",
            "stars": r.get("stargazers_count", 0),
            "pushed_at": (r.get("pushed_at") or "")[:10],
            "topics": r.get("topics") or [],
        }
        for r in repos
        if not r.get("fork") and not r.get("archived") and not r.get("private")
    ]
    cleaned.sort(key=lambda r: r["pushed_at"], reverse=True)

    OUT.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(cleaned)} repos to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
