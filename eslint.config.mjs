import js from '@eslint/js';
import tseslint from 'typescript-eslint';
export default [
  { ignores: ['**/build/**', '**/node_modules/**', '**/.react-router/**', '**/.venv/**', '**/schema.d.ts'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  { files: ['**/*.mjs', '**/*.ts', '**/*.tsx'], languageOptions: { globals: { process: 'readonly', console: 'readonly', URL: 'readonly', fetch: 'readonly', Response: 'readonly', AbortController: 'readonly', setTimeout: 'readonly', clearTimeout: 'readonly' } } },
];
