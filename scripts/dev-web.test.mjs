import { EventEmitter } from 'node:events';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { describe, expect, it, vi } from 'vitest';

const { spawn } = vi.hoisted(() => ({ spawn: vi.fn() }));
vi.mock('node:child_process', () => ({ spawn }));

describe('standalone web launcher privacy', () => {
  it('routes the supported workspace dev command through the safe wrapper', async () => {
    const manifest = JSON.parse(await readFile(new URL('../apps/web/package.json', import.meta.url), 'utf8'));
    expect(manifest.scripts.dev).toBe('node ../../scripts/dev-web.mjs');
  });

  it('preserves other diagnostics and settings when spawning the web process', async () => {
    const { launchWebDevelopment } = await import('./dev-web.mjs');
    spawn.mockReset();
    spawn.mockImplementation(() => new EventEmitter());
    const stop = launchWebDevelopment({ DEBUG: '*,-vite:proxy,app:*', SYNTHETIC_SETTING: 'kept' });
    expect(spawn).toHaveBeenCalledTimes(1);
    const [command, args, options] = spawn.mock.calls[0];
    expect(command).toBe('react-router');
    expect(args).toEqual(['dev', '--host', '127.0.0.1']);
    expect(options.env.DEBUG).toBe('*,app:*,-vite:proxy,-vite:time');
    expect(options.env.SYNTHETIC_SETTING).toBe('kept');
    stop(0);
  });

  it('forwards CLI arguments while preserving private defaults and shutdown', async () => {
    const { launchWebDevelopment } = await import('./dev-web.mjs');
    const child = new EventEmitter();
    child.pid = 123;
    child.kill = vi.fn();
    spawn.mockReset();
    spawn.mockReturnValue(child);
    const interrupts = process.listenerCount('SIGINT');
    const terminations = process.listenerCount('SIGTERM');
    const args = ['--port', '15173', '--strictPort', '--mode', 'private preview'];
    const stop = launchWebDevelopment({ DEBUG: '*', SYNTHETIC_SETTING: 'kept' }, args);
    try {
      expect(spawn).toHaveBeenCalledExactlyOnceWith('react-router', [
        'dev', '--host', '127.0.0.1', '--port', '15173', '--strictPort', '--mode', 'private preview',
      ], {
        stdio: 'inherit', shell: process.platform === 'win32',
        env: { DEBUG: '*,-vite:proxy,-vite:time', SYNTHETIC_SETTING: 'kept' },
      });
      expect(args).toEqual(['--port', '15173', '--strictPort', '--mode', 'private preview']);
      expect(process.listenerCount('SIGINT')).toBe(interrupts + 1);
      expect(process.listenerCount('SIGTERM')).toBe(terminations + 1);
    } finally {
      stop(0);
    }
    expect(process.listenerCount('SIGINT')).toBe(interrupts);
    expect(process.listenerCount('SIGTERM')).toBe(terminations);
    expect(child.kill).toHaveBeenCalledExactlyOnceWith('SIGTERM');
    stop(0);
    expect(child.kill).toHaveBeenCalledTimes(1);
  });

  it('forwards command-line arguments from the standalone entrypoint', async () => {
    const child = new EventEmitter();
    spawn.mockReset();
    spawn.mockReturnValue(child);
    const entryProcess = {
      argv: [process.execPath, fileURLToPath(new URL('./dev-web.mjs', import.meta.url)), '--port', '15173', '--strictPort'],
      env: { DEBUG: '*' }, platform: process.platform,
      on: vi.fn(), removeListener: vi.fn(), exitCode: undefined,
    };
    vi.resetModules();
    vi.stubGlobal('process', entryProcess);
    try {
      await import('./dev-web.mjs');
      expect(spawn).toHaveBeenCalledExactlyOnceWith('react-router', [
        'dev', '--host', '127.0.0.1', '--port', '15173', '--strictPort',
      ], {
        stdio: 'inherit', shell: entryProcess.platform === 'win32',
        env: { DEBUG: '*,-vite:proxy,-vite:time' },
      });
      child.emit('exit', 0);
      expect(entryProcess.exitCode).toBe(0);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
