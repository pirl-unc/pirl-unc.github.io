#!/bin/bash
# Startup script for the "feed-fetcher" VM. Cloud Scheduler starts the VM every
# hour; it refreshes the blog cache from a non-GitHub IP, uploads it, then powers off.
set -uo pipefail
trap 'shutdown -h now' EXIT
# Power off even if a step hangs: a VM left running ignores the hourly start.
(sleep 900; shutdown -h now) &
# Each boot used to leave its clone behind until the 10 GB disk filled up.
find /opt -maxdepth 1 -name 'site-*' -exec rm -rf {} +
rm -f /tmp/blog-cache.tar.gz

meta() { curl -fs -H 'Metadata-Flavor: Google' "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"; }
BUCKET=$(meta bucket)
REF=$(meta ref || echo main)

apt-get update -qq
apt-get install -y -qq git python3-yaml curl

WORK=/opt/site-work
git clone --depth 1 --branch "$REF" https://github.com/pirl-unc/pirl-unc.github.io "$WORK" || exit 1
cd "$WORK" || exit 1
python3 scripts/fetch_posts.py || exit 1
# Never publish a truncated archive: the site build cannot read one.
tar czf /tmp/blog-cache.tar.gz $(ls -d data/posts.json data/posts_status.json static/assets/posts 2>/dev/null) \
  && gzip -t /tmp/blog-cache.tar.gz || exit 1
gcloud storage cp --cache-control=no-cache /tmp/blog-cache.tar.gz "gs://$BUCKET/blog-cache.tar.gz"
