#!/usr/bin/env bash
set -euo pipefail
cert=/etc/letsencrypt/live/issuedigest.projects.ai.kr/fullchain.pem
if [[ ! -s "$cert" ]]; then
  certbot certonly --webroot -w /var/www/certbot -d issuedigest.projects.ai.kr \
    --non-interactive --agree-tos --register-unsafely-without-email
fi
site=/etc/nginx/sites-available/issuedigest.projects.ai.kr
backup=$(mktemp /etc/nginx/backups/issuedigest-before-https.XXXXXX)
cp "$site" "$backup"
install -m 644 /usr/local/libexec/issuedigest/nginx.conf "$site"
if ! nginx -t; then
  cp "$backup" "$site"
  echo 'HTTPS configuration rejected; previous configuration restored' >&2
  exit 1
fi
/etc/letsencrypt/renewal-hooks/deploy/00-reload-nginx.sh
systemctl disable --now issuedigest-tls.timer
echo 'IssueDigest HTTPS enabled'
