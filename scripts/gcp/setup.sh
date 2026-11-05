#!/usr/bin/env bash
# One-time setup of the hourly blog-feed fetcher in Google Cloud. Safe to re-run:
# resources that already exist are left alone.
#
# Creates: a public-read bucket (blog posts + covers only), two service accounts,
# a stopped e2-micro VM that fetches the feed and uploads the cache, and a Cloud
# Scheduler job that starts it every hour. Costs well under $1/month.
#
#   PROJECT=my-project ./scripts/gcp/setup.sh
set -euo pipefail
cd "$(dirname "$0")"
P=${PROJECT:?set PROJECT}; Z=us-east1-b; R=us-east1
B=${BUCKET:-pirl-site-feed-$P}
REF=${REF:-main}
VM_SA=feed-vm@$P.iam.gserviceaccount.com
SCHED_SA=feed-scheduler@$P.iam.gserviceaccount.com

gcloud services enable compute.googleapis.com storage.googleapis.com cloudscheduler.googleapis.com --project "$P"

gcloud storage buckets create "gs://$B" --project "$P" --location "$R" --uniform-bucket-level-access || true
gcloud iam service-accounts create feed-vm --project "$P" --display-name "PIRL feed fetcher VM" || true
gcloud iam service-accounts create feed-scheduler --project "$P" --display-name "PIRL feed scheduler" || true
sleep 10

gcloud storage buckets add-iam-policy-binding "gs://$B" --member "serviceAccount:$VM_SA" --role roles/storage.objectAdmin
# Public read: the cache contains only public blog posts and cover images.
gcloud storage buckets add-iam-policy-binding "gs://$B" --member allUsers --role roles/storage.objectViewer
gcloud projects add-iam-policy-binding "$P" --member "serviceAccount:$SCHED_SA" --role roles/compute.instanceAdmin.v1 --condition=None

gcloud compute instances create feed-fetcher --project "$P" --zone "$Z" \
  --machine-type e2-micro --image-family debian-12 --image-project debian-cloud \
  --service-account "$VM_SA" --scopes cloud-platform \
  --metadata "bucket=$B,ref=$REF" --metadata-from-file startup-script=feed_vm_startup.sh || true

# The first boot runs the script and powers the VM off; wait for that.
echo "Waiting for the first run to finish..."
for _ in $(seq 40); do
  status=$(gcloud compute instances describe feed-fetcher --project "$P" --zone "$Z" --format='value(status)')
  [ "$status" = TERMINATED ] && break
  sleep 10
done

gcloud scheduler jobs create http feed-fetch --project "$P" --location "$R" \
  --schedule "7 * * * *" --time-zone UTC --http-method POST \
  --uri "https://compute.googleapis.com/compute/v1/projects/$P/zones/$Z/instances/feed-fetcher/start" \
  --oauth-service-account-email "$SCHED_SA" || true

echo "Done. Cache URL: https://storage.googleapis.com/$B/blog-cache.tar.gz"
