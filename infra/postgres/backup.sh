#!/bin/bash
set -euo pipefail
umask 077
backup_dir=/srv/issuedigest/postgres/backups
mkdir -p "$backup_dir"
exec 9>"$backup_dir/.backup.lock"
flock -n 9
stamp=$(date -u +%Y%m%dT%H%M%SZ)
dump="$backup_dir/issuedigest-$stamp.dump"
partial="$dump.partial"
trap 'rm -f "$partial"' EXIT
docker exec issuedigest-postgres pg_dump -U postgres -Fc issuedigest > "$partial"
docker exec -i issuedigest-postgres pg_restore --list < "$partial" > /dev/null
mv "$partial" "$dump"
docker exec issuedigest-postgres pg_dumpall -U postgres --roles-only > "$backup_dir/roles-$stamp.sql"
echo "Backup created: $dump"
