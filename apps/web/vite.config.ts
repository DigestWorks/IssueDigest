import { reactRouter } from '@react-router/dev/vite';
import { stripVTControlCharacters } from 'node:util';
import { createLogger, defineConfig, type Logger } from 'vite';

/** Keep API proxy failures useful without logging request URLs or provider errors. */
function createDevelopmentLogger(): Logger {
  const logger = createLogger();
  const originalError = logger.error.bind(logger);
  logger.error = (message, options) => {
    // Vite's proxy matcher uses the same /api prefix; color escapes are presentation only.
    if (/^http proxy error:\s*\/api/.test(stripVTControlCharacters(message))) {
      originalError('API proxy request failed', { timestamp: options?.timestamp === true });
      return;
    }
    originalError(message, options);
  };
  return logger;
}

// Server-side development setting only; never exposed through a VITE_* variable.
const target = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000';
export default defineConfig({
  customLogger: createDevelopmentLogger(),
  plugins: [reactRouter()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target }, '/health': { target } },
  },
});
