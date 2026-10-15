#!/usr/bin/env python3
"""Build the site into _site/.

    python build.py            # build
    python -m http.server -d _site 8000   # preview at http://localhost:8000

Content lives in data/*.yml. Blog posts and the repo list come from
data/posts.json and data/repos.json, which the GitHub Action refreshes
(see scripts/). Templates are in templates/, static files in static/.
"""

import json
import os
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATIC = ROOT / "static"
OUT = ROOT / os.environ.get("OUTPUT_DIR", "_site")

# page name -> (template, output path)
PAGES = {
    "index": ("index.html", "index.html"),
    "people": ("people.html", "people/index.html"),
    "papers": ("papers.html", "papers/index.html"),
    "code": ("code.html", "code/index.html"),
    "contact": ("contact.html", "contact/index.html"),
    "404": ("404.html", "404.html"),
}

# Old Squarespace URLs that should keep working.
REDIRECTS = {
    "research/index.html": "/papers/",
}


def load_yaml(name):
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))


def load_json(name, default):
    path = DATA / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def nice_date(value):
    """'2025-03-07' -> 'Mar 7, 2025'"""
    if not value:
        return ""
    try:
        d = date.fromisoformat(value[:10])
    except ValueError:
        return value
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def main():
    # Only disposable build directories may be recursively replaced.
    if OUT.is_symlink() or OUT.resolve() not in {ROOT / "_site", ROOT / "dist"}:
        raise ValueError("OUTPUT_DIR must be _site or dist inside the project")
    site = load_yaml("site.yml")
    site["url"] = os.environ.get("SITE_URL", site["url"]).rstrip("/")
    site["source_url"] = os.environ.get("SOURCE_URL", site["source_url"])
    # A project Pages site lives below /repo/; a custom domain lives at /.
    base_path = urlsplit(site["url"]).path.rstrip("/")

    def site_path(path):
        if path.startswith("/") and not path.startswith("//"):
            return base_path + path
        return path

    def absolute_url(path):
        if path.startswith("/") and not path.startswith("//"):
            origin = urlsplit(site["url"])
            return f"{origin.scheme}://{origin.netloc}{path}"
        return path
    people = load_yaml("people.yml")
    papers = load_yaml("papers.yml")
    tools = load_yaml("tools.yml")
    contact = load_yaml("contact.yml")
    appearance = load_yaml("appearance.yml")
    posts = load_json("posts.json", [])
    repos = load_json("repos.json", [])

    hidden = set(tools.get("hide_repos") or [])
    repos = [r for r in repos if r["name"] not in hidden]

    def asset(local, remote=None):
        """Prefer a committed local file; fall back to the remote (Squarespace) URL."""
        if (STATIC / local).exists():
            return site_path("/" + local)
        return remote or site_path("/" + local)

    def photo(person):
        if person.get("photo") and (STATIC / "assets" / "people" / person["photo"]).exists():
            return site_path("/assets/people/" + person["photo"])
        return person.get("photo_url") or ""

    def post_image(post):
        local = post.get("image_local")
        if local and (STATIC / local).is_file():
            return site_path("/" + local)
        # Serve only downloaded covers: blocked CDNs should not break the page.
        return ""

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["nice_date"] = nice_date
    env.globals.update(
        site=site,
        site_path=site_path,
        absolute_url=absolute_url,
        asset=asset,
        photo=photo,
        post_image=post_image,
    )

    context = {
        "people": people,
        "papers": papers,
        "tools": tools,
        "contact": contact,
        "appearance": appearance,
        "posts": posts,
        "recent_posts": posts[: site.get("recent_posts", 6)],
        "repos": repos,
    }

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    (OUT / ".nojekyll").write_text("")

    for name, (template, out_path) in PAGES.items():
        html = env.get_template(template).render(page=name, **context)
        dest = OUT / out_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        print(f"  {out_path}")

    for out_path, target in REDIRECTS.items():
        target = site_path(target)
        dest = OUT / out_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            f'<!doctype html><meta charset="utf-8"><title>Redirecting</title>'
            f'<meta http-equiv="refresh" content="0; url={target}">'
            f'<link rel="canonical" href="{absolute_url(target)}"><a href="{target}">Continue</a>',
            encoding="utf-8",
        )
        print(f"  {out_path} -> {target}")

    print(f"Built {len(PAGES)} pages, {len(posts)} posts, {len(repos)} repos into {OUT.name}/")


if __name__ == "__main__":
    main()
