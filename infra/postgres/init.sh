#!/bin/sh
set -eu
export DEVELOPER_PASSWORD="$(cat /run/secrets/developer_password)"
export APP_PASSWORD="$(cat /run/secrets/app_password)"
psql -v ON_ERROR_STOP=1 -U postgres -d postgres -f /opt/issuedigest/init.sql
unset DEVELOPER_PASSWORD APP_PASSWORD
