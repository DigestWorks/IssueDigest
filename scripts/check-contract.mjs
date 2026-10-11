import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const temporary = mkdtempSync(join(tmpdir(), 'issuedigest-contract-'));
try {
  const schema = join(temporary, 'openapi.json');
  const types = join(temporary, 'schema.d.ts');
  execFileSync('uv', ['run', '--package', 'issuedigest-api', 'python', 'scripts/export_openapi.py', schema], { stdio: 'inherit' });
  execFileSync(process.execPath, ['node_modules/openapi-typescript/bin/cli.js', schema, '-o', types], { stdio: 'inherit' });
  for (const [generated, committed] of [[schema, 'packages/api-client/openapi.json'], [types, 'packages/api-client/src/schema.d.ts']]) {
    if (!readFileSync(generated).equals(readFileSync(committed))) {
      throw new Error(`Contract drift: ${committed}. Run npm run contract:generate and review both generated files.`);
    }
  }
  console.log('OpenAPI and TypeScript contracts are up to date.');
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
