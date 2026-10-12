import { defineConfig } from 'vitest/config';
export default defineConfig({
  test: {
    projects: [
      { test: { name: 'client', environment: 'node', include: ['packages/api-client/tests/**/*.test.ts'] } },
      { test: { name: 'web', environment: 'jsdom', include: ['apps/web/tests/**/*.test.tsx'], setupFiles: ['apps/web/tests/setup.ts'] } },
      { test: { name: 'ui', environment: 'jsdom', include: ['packages/ui/tests/**/*.test.tsx'], setupFiles: ['packages/ui/tests/setup.ts'] } },
    ],
  },
});
