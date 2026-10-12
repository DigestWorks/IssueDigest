#!/usr/bin/env python3
"""Run as root on Oracle-Server. Publish read-only references and a scoped SQL login."""
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import shutil
import subprocess

ACCOUNT = 'DigestWorks_Jaesin'
REPO = Path('/home/ubuntu/project/Lawdigest')
REFERENCE = Path('/srv/issuedigest/reference')
SQL_USER = 'issuedigest_jaesin_ro'
SQL_TABLES = '''Bill BillAlternative BillProposer BillReportTooltip BillSearchDocument
BillSummaryTag BillTimeline Congressman IngestCheckpoint LegalTermDictionary Party
PollCatalog PollOption PollQuestion PollSurvey RepresentativeProposer VoteParty
VoteRecord election_candidates election_codes election_districts election_educations
election_gusiguns election_jobs election_parties election_party_policies
election_pledges election_winners'''.split()
SOURCES = {
    'bills': REPO / 'services/data/output/bills',
    'elections': REPO / 'services/data/output/elections',
    'parsed': REPO / 'services/data/output/parsed',
    'pdfs': REPO / 'services/data/output/pdfs',
    'polls': REPO / 'services/data/output/polls',
    'ai-output': REPO / 'services/ai/output',
    'legacy-data': Path('/home/ubuntu/project/data_job/data'),
    'legacy-output': Path('/home/ubuntu/project/data_job/output'),
}

def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs)

if os.geteuid() != 0:
    raise SystemExit('Run as root on Oracle-Server')
if REFERENCE.exists():
    raise SystemExit('Reference directory exists; inspect it before changing access')
account = pwd.getpwnam(ACCOUNT)
for p in SOURCES.values():
    if not p.is_dir():
        raise SystemExit(f'Missing source: {p}')
config = Path(account.pw_dir) / '.config/issuedigest'
for name in ('legacy-mysql.cnf', 'legacy-data.env'):
    if (config / name).exists():
        raise SystemExit(f'Existing credentials: {name}')

# Secret values stay on the server and are never printed or copied to the repository.
secret_values = set()
for p in REPO.glob('services/*/.env'):
    for line in p.read_text().splitlines():
        match = re.match(r'(?:export\s+)?([A-Z_0-9]+)\s*=\s*(.*)', line)
        if match and any(k in match[1] for k in ('PASSWORD', 'SECRET', 'TOKEN', 'API_KEY')):
            value = match[2].strip().strip('\"\x27')
            if len(value) >= 6:
                secret_values.add(value)

REFERENCE.mkdir(mode=0o750)
run(['setfacl', '-m', f'u:{ACCOUNT}:rx', str(REFERENCE)])
code = REFERENCE / 'code'
code.mkdir(mode=0o755)
tracked = run(['git', '-C', str(REPO), 'ls-files', 'services/backend', 'services/ai',
               'services/data', 'docs/data', 'docs/ai', 'almanac'], text=True).stdout.splitlines()
redacted = []
copied = 0
for relative in tracked:
    source = REPO / relative
    if (not source.is_file() or source.is_symlink()
        or any(part in ('output', 'build', 'logs', '__pycache__', '.venv') for part in source.parts)
        or source.name.startswith('.env') and source.name != '.env.example'
        or source.suffix in ('.pem', '.key', '.p12', '.sql')):
        continue
    raw = source.read_bytes()
    try:
        content = raw.decode('utf-8')
    except UnicodeDecodeError:
        continue
    if 'PRIVATE KEY-----' in content:
        continue
    original = content
    for value in sorted(secret_values, key=len, reverse=True):
        content = content.replace(value, '[REDACTED]')
    # Redact literal credentials and URL userinfo in reference copies only.
    content = re.sub(r'(?im)(\b(?:password|passwd|api[_-]?key|secret|token)\s*[:=]\s*)[\x27\x22][^\x27\x22\n]+[\x27\x22]', r'\1"[REDACTED]"', content)
    content = re.sub(r'(?i)((?:postgres(?:ql)?|mysql)://)[^\s/:]+:[^\s/@]+@', r'\1[REDACTED]@', content)
    content = re.sub(r'(?im)^(\s*(?:password|secret|api-key|api_key)\s*:\s*)[^\n]+', r'\1[REDACTED]', content)
    content = re.sub(r'''(?i)((?:os\.)?getenv\(\s*[\x27\x22][A-Z_]*(?:PASSWORD|TOKEN|SECRET|API_KEY)[A-Z_]*[\x27\x22]\s*,\s*)[\x27\x22][^\x27\x22\n]+[\x27\x22]''', r'\1"[REDACTED]"', content)
    target = code / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    target.chmod(0o444)
    if content != original:
        redacted.append(relative)
    copied += 1

# Export only status fields from the operational log; raw parameters stay private.
status_source = Path('/tmp/lawdigest-pipeline/pipeline-runs.jsonl')
if status_source.exists():
    status = REFERENCE / 'status'
    status.mkdir(mode=0o755)
    with status_source.open() as source, (status / 'pipeline-runs.jsonl').open('w') as target:
        for line in source:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            safe = {key: entry[key] for key in ('event', 'run_id', 'timestamp') if key in entry}
            target.write(json.dumps(safe, ensure_ascii=False) + '\n')
    (status / 'pipeline-runs.jsonl').chmod(0o444)

# Publish specific raw-data directories; database dumps are excluded.
data = REFERENCE / 'data'
data.mkdir(mode=0o755)
fstab_lines = []
for name, source in SOURCES.items():
    target = data / name
    target.mkdir(mode=0o755)
    run(['setfacl', '-R', '-m', f'u:{ACCOUNT}:rX', str(source)])
    for directory, _, _ in os.walk(source, followlinks=False):
        run(['setfacl', '-m', f'd:u:{ACCOUNT}:rx', directory])
    run(['mount', '--bind', str(source), str(target)])
    run(['mount', '-o', 'remount,bind,ro,nosuid,nodev,noexec', str(target)])
    fstab_lines.append(f'{source} {target} none bind,ro,nosuid,nodev,noexec,nofail 0 0')
for source in (REPO / 'services/data/output').iterdir():
    if source.is_file() and source.suffix in ('.json', '.csv'):
        target = data / source.name
        shutil.copyfile(source, target)
        target.chmod(0o444)
backup = Path('/srv/issuedigest/fstab-before-reference')
shutil.copy2('/etc/fstab', backup)
backup.chmod(0o600)
with open('/etc/fstab', 'a') as f:
    f.write('\n# IssueDigest read-only collected data\n' + '\n'.join(fstab_lines) + '\n')
run(['systemctl', 'daemon-reload'])

# Local TCP arrives through the MySQL container's bridge gateway.
info = json.loads(run(['docker', 'inspect', 'mysql'], text=True).stdout)[0]
container_env = dict(value.split('=', 1) for value in info['Config']['Env'])
root_env = dict(os.environ, MYSQL_PWD=container_env['MYSQL_ROOT_PASSWORD'])
mysql = ['mysql', '--protocol=TCP', '-h127.0.0.1', '-P2835', '-uroot', '-N']
source_user = run(mysql, input='SELECT USER();', env=root_env, text=True).stdout.strip()
host = source_user.split('@', 1)[1]
if not re.fullmatch(r'[0-9.]+', host):
    raise SystemExit('Expected a local bridge IPv4 address')
password = secrets.token_urlsafe(36)
identity = f"'{SQL_USER}'@'{host}'"
statements = [f"CREATE USER {identity} IDENTIFIED BY '{password}' WITH MAX_USER_CONNECTIONS 3;"]
statements += [f'GRANT SELECT ON `lawDB`.`{table}` TO {identity};' for table in SQL_TABLES]
run(mysql, input='\n'.join(statements), env=root_env, text=True)
config.mkdir(mode=0o700, parents=True, exist_ok=True)
credentials = {
    'legacy-mysql.cnf': f'[client]\nhost=127.0.0.1\nport=2835\nuser={SQL_USER}\npassword={password}\nprotocol=TCP\n',
    'legacy-data.env': f'export LEGACY_MYSQL_HOST=127.0.0.1\nexport LEGACY_MYSQL_PORT=2835\nexport LEGACY_MYSQL_DATABASE=lawDB\nexport LEGACY_MYSQL_USER={SQL_USER}\nexport LEGACY_MYSQL_CONFIG={config}/legacy-mysql.cnf\nexport LEGACY_REFERENCE_ROOT={REFERENCE}\n',
}
for name, content in credentials.items():
    p = config / name
    p.write_text(content)
    p.chmod(0o600)
    os.chown(p, account.pw_uid, account.pw_gid)
wrapper = Path(account.pw_dir) / '.local/bin/issuedigest-legacy-db'
if wrapper.exists():
    raise SystemExit('Existing DB wrapper found')
wrapper.parent.mkdir(parents=True, exist_ok=True)
wrapper.write_text('#!/bin/bash\nset -euo pipefail\nexec mysql --defaults-extra-file="$HOME/.config/issuedigest/legacy-mysql.cnf" --database=lawDB --init-command="SET SESSION MAX_EXECUTION_TIME=30000" "$@"\n')
wrapper.chmod(0o700)
os.chown(wrapper, account.pw_uid, account.pw_gid)
manifest = {
    'source_repository': str(REPO),
    'source_commit': run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).stdout.strip(),
    'code_snapshot_files': copied,
    'redacted_files': redacted,
    'live_readonly_mounts': {name: str(path) for name, path in SOURCES.items()},
    'mysql_container': 'mysql', 'mysql_database': 'lawDB', 'mysql_port': 2835,
    'mysql_login': SQL_USER, 'mysql_login_host': host, 'select_tables': SQL_TABLES,
    'code_snapshot_note': 'Tracked working-tree files; secret settings removed. Source checkout unchanged.',
}
(REFERENCE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
(REFERENCE / 'manifest.json').chmod(0o444)
print('Read-only references and scoped MySQL account provisioned; credentials not printed')
