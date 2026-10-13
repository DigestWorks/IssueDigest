import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { protectedDevelopmentEnvironment } from './dev-environment.mjs';

// Each process group includes its reload children, so stopping dev closes both apps.
export function launchDevelopment(environment = process.env, apiOnly = false) {
  const configured = environment.ISSUEDIGEST_CONFIGURED_RUNTIME === '1';
  const apiArgs = [
    'run', '--package', 'issuedigest-api', 'uvicorn',
    configured ? 'issuedigest_api.runtime:create_configured_app' : 'issuedigest_api.main:app',
    ...(configured ? ['--factory'] : []),
    '--no-access-log', '--reload', '--host', '127.0.0.1', '--port', '8000',
  ];
  const commands = [['uv', apiArgs], ...(apiOnly ? [] : [['npm', ['run', 'dev:web']]])];
  const children = commands.map(([command, args]) => spawn(command, args, {
    env: protectedDevelopmentEnvironment(environment),
    stdio: 'inherit', detached: process.platform !== 'win32', shell: process.platform === 'win32',
  }));
  let stopping = false;
  const onInterrupt = () => stop(0);
  function stop(code) {
    if (stopping) return;
    stopping = true;
    process.exitCode = code;
    process.removeListener('SIGINT', onInterrupt);
    process.removeListener('SIGTERM', onInterrupt);
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
  process.on('SIGINT', onInterrupt);
  process.on('SIGTERM', onInterrupt);
  return stop;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  launchDevelopment(process.env, process.argv.includes('--api-only'));
}
