import { EventEmitter } from 'node:events';
import { describe, expect, it, vi } from 'vitest';

const { spawn } = vi.hoisted(() => ({ spawn: vi.fn(() => ({ on: () => {} })) }));
vi.mock('node:child_process', () => ({ spawn }));

import { launchDevelopment } from './dev.mjs';

describe('development process selection', () => {
  it.each([
    [{}, 'issuedigest_api.main:app', false],
    [{ ISSUEDIGEST_CONFIGURED_RUNTIME: '0' }, 'issuedigest_api.main:app', false],
    [{ ISSUEDIGEST_CONFIGURED_RUNTIME: '1' }, 'issuedigest_api.runtime:create_configured_app', true],
  ])('selects the explicit runtime only on opt-in %j', (environment, target, factory) => {
    spawn.mockReset();
    spawn.mockImplementation(() => new EventEmitter());
    const stop = launchDevelopment(environment, true);
    expect(spawn).toHaveBeenCalledTimes(1);
    const [command, args] = spawn.mock.calls[0];
    expect(command).toBe('uv');
    expect(args).toContain(target);
    expect(args).toContain('--no-access-log');
    expect(args.includes('--factory')).toBe(factory);
    stop(0);
  });

  it('launches both default apps without reading credentials', () => {
    spawn.mockReset();
    spawn.mockImplementation(() => new EventEmitter());
    const stop = launchDevelopment({});
    expect(spawn.mock.calls.map(([command]) => command)).toEqual(['uv', 'npm']);
    stop(0);
  });
});
