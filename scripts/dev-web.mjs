import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { protectedDevelopmentEnvironment } from './dev-environment.mjs';

export function launchWebDevelopment(environment = process.env, args = []) {
  const child = spawn('react-router', ['dev', '--host', '127.0.0.1', ...args], {
    stdio: 'inherit', shell: process.platform === 'win32',
    env: protectedDevelopmentEnvironment(environment),
  });
  let stopping = false;
  const onInterrupt = () => stop(0);
  function stop(code) {
    if (stopping) return;
    stopping = true;
    process.exitCode = code;
    process.removeListener('SIGINT', onInterrupt);
    process.removeListener('SIGTERM', onInterrupt);
    if (child.pid) child.kill('SIGTERM');
  }
  child.on('error', () => { console.error('Web development process failed'); stop(1); });
  child.on('exit', (code) => stop(code ?? 1));
  process.on('SIGINT', onInterrupt);
  process.on('SIGTERM', onInterrupt);
  return stop;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  launchWebDevelopment(process.env, process.argv.slice(2));
}
