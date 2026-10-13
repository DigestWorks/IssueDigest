#!/usr/bin/env bash
set -Eeuo pipefail
umask 027
export PATH=/opt/issuedigest-tools/node-v24.21.0-linux-arm64/bin:/opt/issuedigest-tools:/usr/bin:/bin
base=/srv/issuedigest
sha=${1:?Usage: deploy.sh COMMIT_SHA}
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid commit SHA' >&2; exit 2; }
exec 9>"$base/shared/deploy.lock"
flock -n 9 || { echo 'Another deployment is running' >&2; exit 1; }
git -C "$base/repo" fetch origin main
head=$(git -C "$base/repo" rev-parse origin/main)
[[ "$head" == "$sha" ]] || { echo 'Commit is no longer the main head; refusing stale deployment' >&2; exit 1; }
for file in package.json package-lock.json pyproject.toml uv.lock .nvmrc .python-version apps/web/package.json apps/api/src/issuedigest_api/main.py; do
  git -C "$base/repo" cat-file -e "$sha:$file" || { echo "Application not ready: $file" >&2; exit 1; }
done
release="$base/releases/$sha-$(date -u +%Y%m%dT%H%M%S)-$$"
mkdir "$release"
git -C "$base/repo" archive "$sha" | tar -x -C "$release"
cd "$release"
[[ "$(cat .nvmrc)" == "24.21.0" && "$(cat .python-version)" == "3.13.12" ]] || { echo 'Runtime pins changed; administrator must update tools first' >&2; exit 1; }
npm ci
uv python install 3.13.12
uv sync --locked --all-packages --no-dev
npm run build
test -s apps/web/build/client/index.html
# Public static assets only; application sources remain group-readable.
setfacl -m u:www-data:x "$release" "$release/apps" "$release/apps/web" "$release/apps/web/build"
setfacl -R -m u:www-data:rX "$release/apps/web/build/client"
previous=$(readlink "$base/current" || true)
candidate_pid=''
promoted=0
cleanup() {
  result=$?
  trap - EXIT
  if [[ -n "$candidate_pid" ]]; then
    kill "$candidate_pid" 2>/dev/null || true
    wait "$candidate_pid" 2>/dev/null || true
  fi
  if (( result != 0 && promoted )); then
    if [[ -n "$previous" ]]; then
      ln -s "$previous" "$base/current.rollback"
      mv -Tf "$base/current.rollback" "$base/current"
      sudo -n /usr/bin/systemctl restart issuedigest-api.service
      echo 'Previous release restored' >&2
    else
      sudo -n /usr/bin/systemctl stop issuedigest-api.service
      unlink "$base/current"
      echo 'First release failed; no release is active' >&2
    fi
  fi
  exit "$result"
}
trap cleanup EXIT
healthy() {
  curl --fail --silent --max-time 3 "$1/health/live" | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "ok"' &&
  curl --fail --silent --max-time 3 "$1/api/v1/status" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["service"] == "issuedigest-api" and d["status"] == "ok"'
}
.venv/bin/uvicorn issuedigest_api.main:app --host 127.0.0.1 --port 18191 >"$base/shared/candidate.log" 2>&1 &
candidate_pid=$!
ready=0
for attempt in {1..30}; do
  if healthy http://127.0.0.1:18191 && kill -0 "$candidate_pid"; then ready=1; break; fi
  sleep 1
done
(( ready )) || { echo 'Candidate API health check failed' >&2; exit 1; }
kill "$candidate_pid"
wait "$candidate_pid" || true
candidate_pid=''
# A push during the build must not publish an older head.
git -C "$base/repo" fetch origin main
[[ "$(git -C "$base/repo" rev-parse origin/main)" == "$sha" ]] || { echo 'Main changed during build; refusing stale deployment' >&2; exit 1; }
ln -s "$release" "$base/current.next"
mv -Tf "$base/current.next" "$base/current"
promoted=1
sudo -n /usr/bin/systemctl restart issuedigest-api.service
ready=0
for attempt in {1..30}; do
  if healthy https://issuedigest.projects.ai.kr && curl --fail --silent --max-time 5 https://issuedigest.projects.ai.kr/ -o /dev/null; then ready=1; break; fi
  sleep 1
done
(( ready )) || { echo 'Public health check failed' >&2; exit 1; }
printf '%s\n' "$sha" > "$base/shared/deployed-sha"
echo "Deployed $sha"
