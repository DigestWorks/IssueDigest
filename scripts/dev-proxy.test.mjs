import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLogger } from 'vite';
import config from '../apps/web/vite.config.ts';

const logger = config.customLogger ?? createLogger();
afterEach(() => vi.restoreAllMocks());

describe('development API proxy privacy', () => {
  it.each([
    'http proxy error: /api/v1/auth/google/callback?code=PRIVATE_CODE&state=PRIVATE_STATE\nPRIVATE_STACK',
    '\u001b[31mhttp proxy error: /api/v1/auth/google/callback?code=PRIVATE_CODE&state=PRIVATE_STATE\u001b[39m\nPRIVATE_STACK',
    'http proxy error: /api/v1/auth/session\nCookie: PRIVATE_SESSION',
  ])('replaces only API proxy diagnostics and discards the error object', (message) => {
    const output = vi.spyOn(console, 'error').mockImplementation(() => {});
    const error = new Error('PRIVATE_PROVIDER_ERROR');
    error.stack = 'PRIVATE_STACK';
    logger.error(message, { timestamp: true, environment: 'PRIVATE_ENVIRONMENT', error });
    expect(output).toHaveBeenCalledTimes(1);
    const emitted = output.mock.calls.flat().join(' ');
    expect(emitted).toContain('API proxy request failed');
    expect(emitted).not.toContain('PRIVATE');
    expect(emitted).not.toContain('/api/');
    expect(logger.hasErrorLogged(error)).toBe(false);
    expect(logger.hasWarned).toBe(true);
  });

  it('preserves unrelated build errors, health proxy diagnostics, and warnings', () => {
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {});
    const warnings = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const error = new Error('synthetic build diagnostic');
    logger.error('synthetic build diagnostic', { error });
    logger.error('http proxy error: /health/live\nsynthetic connection error');
    logger.warn('synthetic warning');
    expect(errors.mock.calls).toEqual([
      ['synthetic build diagnostic'],
      ['http proxy error: /health/live\nsynthetic connection error'],
    ]);
    expect(warnings).toHaveBeenCalledWith('synthetic warning');
    expect(logger.hasErrorLogged(error)).toBe(true);
  });
});
