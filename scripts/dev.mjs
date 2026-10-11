import { spawn } from 'node:child_process';

// Each process group includes its reload children, so stopping dev closes both apps.
const commands = [
  ['uv', ['run', '--package', 'issuedigest-api', 'uvicorn', 'issuedigest_api.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000']],
  ['npm', ['run', 'dev:web']],
];
const children = commands.map(([command, args]) => spawn(command, args, {
  stdio: 'inherit', detached: process.platform !== 'win32', shell: process.platform === 'win32',
}));
let stopping = false;
function stop(code) {
  if (stopping) return;
  stopping = true;
  process.exitCode = code;
  for (const child of children) {
    if (!child.pid) continue;
    try {
      if (process.platform === 'win32') child.kill('SIGTERM');
      else process.kill(-child.pid, 'SIGTERM');
    } catch (error) {
      if (error.code !== 'ESRCH') console.error(error);
    }
  }
}
for (const child of children) {
  child.on('error', (error) => { console.error(error); stop(1); });
  child.on('exit', (code) => stop(code ?? 1));
}
process.on('SIGINT', () => stop(0));
process.on('SIGTERM', () => stop(0));
