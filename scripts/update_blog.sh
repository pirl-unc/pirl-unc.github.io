#!/usr/bin/env bash
# Refresh the Substack post cache from this machine and publish it.
#
# GitHub's CI runners get HTTP 403 from Substack, so run this locally after
# publishing a post (the site rebuilds automatically once the push lands).
#
#   ./scripts/update_blog.sh
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/fetch_posts.py

git add data/posts.json data/posts_status.json static/assets/posts/
if git diff --cached --quiet; then
  echo "Blog cache already up to date."
else
  git commit -m "Refresh blog posts"
  git push
  echo "Pushed. The site will rebuild shortly."
fi
