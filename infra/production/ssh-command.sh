#!/usr/bin/env bash
set -euo pipefail
if [[ "${SSH_ORIGINAL_COMMAND:-}" == 'check' ]]; then
  test -r /srv/issuedigest/repo/.git/HEAD
  test -w /srv/issuedigest/releases
  /opt/issuedigest-tools/uv --version
  /opt/issuedigest-tools/node-v24.21.0-linux-arm64/bin/node --version
  echo 'Deployment host ready; no application was deployed'
  exit 0
fi
if [[ "${SSH_ORIGINAL_COMMAND:-}" =~ ^deploy\ ([0-9a-f]{40})$ ]]; then
  exec /usr/local/libexec/issuedigest/deploy.sh "${BASH_REMATCH[1]}"
fi
echo 'Only check or deploy COMMIT_SHA is allowed' >&2
exit 2
