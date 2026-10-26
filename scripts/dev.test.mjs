import { EventEmitter } from 'node:events';
import { describe, expect, it, vi } from 'vitest';

const { spawn } = vi.hoisted(() => ({ spawn: vi.fn(() => ({ on: () => {} })) }));
vi.mock('node:child_process', () => ({ spawn }));

import { launchDevelopment } from './dev.mjs';

describe('development process selection', () => {
  it.each([
    [{}, 'issuedigest_api.main:app', false],
    [{ ISSUEDIGEST_QUESTION_BRIEFING_ENABLED: '1' }, 'issuedigest_api.main:app', false],
    [{ ISSUEDIGEST_CONFIGURED_RUNTIME: '1', ISSUEDIGEST_QUESTION_BRIEFING_ENABLED: '0' }, 'issuedigest_api.runtime:create_configured_app', true],
    [{ ISSUEDIGEST_CONFIGURED_RUNTIME: '1', ISSUEDIGEST_QUESTION_BRIEFING_ENABLED: '1' }, 'scripts.question_briefing_app:create_question_briefing_app', true],
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
    expect(args.includes('--all-packages')).toBe(target.startsWith('scripts.'));
    expect(args.includes('--package')).toBe(!target.startsWith('scripts.'));
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

it('removes sensitive Vite debug namespaces only in the child environment', () => {
  spawn.mockReset();
  spawn.mockImplementation(() => new EventEmitter());
  const environment = { DEBUG: 'vite:*,app:*,other,-app:secret', SYNTHETIC_SETTING: 'kept' };
  const stop = launchDevelopment(environment);
  const options = spawn.mock.calls[1][2];
  expect(options.env?.DEBUG).toBe('vite:*,app:*,other,-app:secret,-vite:proxy,-vite:time');
  expect(options.env?.SYNTHETIC_SETTING).toBe('kept');
  expect(environment.DEBUG).toBe('vite:*,app:*,other,-app:secret');
  stop(0);
});
