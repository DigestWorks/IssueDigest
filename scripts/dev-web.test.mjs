import { EventEmitter } from 'node:events';
import { readFile } from 'node:fs/promises';
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
});
