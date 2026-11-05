#!/bin/bash
# Startup script for the "feed-fetcher" VM. Cloud Scheduler starts the VM every
# hour; it refreshes the blog cache from a non-GitHub IP, uploads it, then powers off.
set -uo pipefail
trap 'shutdown -h now' EXIT

meta() { curl -fs -H 'Metadata-Flavor: Google' "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"; }
BUCKET=$(meta bucket)
REF=$(meta ref || echo main)

apt-get update -qq
apt-get install -y -qq git python3-yaml curl

WORK=/opt/site-$(date +%s)
git clone --depth 1 --branch "$REF" https://github.com/pirl-unc/pirl-unc.github.io "$WORK"
cd "$WORK"
python3 scripts/fetch_posts.py
tar czf /tmp/blog-cache.tar.gz $(ls -d data/posts.json data/posts_status.json static/assets/posts 2>/dev/null)
gcloud storage cp --cache-control=no-cache /tmp/blog-cache.tar.gz "gs://$BUCKET/blog-cache.tar.gz"
