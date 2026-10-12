/** Compile-only consumer of the generated protected path and canonical evidence response. */
import type { components, paths } from '../src/schema';
import type { EvidenceBundle } from '../src/index';

type Operation = paths['/api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}']['get'];
type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;
type Assert<T extends true> = T;
export type ResponseIsCanonicalEvidence = Assert<Equal<
  Operation['responses'][200]['content']['application/json'], EvidenceBundle
>>;
export type ResponseIsGeneratedDomain = Assert<Equal<
  Operation['responses'][200]['content']['application/json'], components['schemas']['EvidenceBundle']
>>;
export const evidenceIds: Operation['parameters']['path'] = {
  workspace_id: 'f3542140-1a33-4e96-8f8b-4601f9951b21',
  snapshot_id: 'c20b131b-9d14-4748-8d9f-3225ea856482',
};
export const protectedHeaders: Operation['responses'][200]['headers'] = {
  'Cache-Control': 'no-store', 'X-Request-ID': 'f3542140-1a33-4e96-8f8b-4601f9951b21',
};
// @ts-expect-error the protected path requires both UUID path parameters
export const incompletePath: Operation['parameters']['path'] = { workspace_id: 'workspace' };
// @ts-expect-error evidence response retains the no-store response contract
export const cachedResponse: Operation['responses'][200]['headers'] = { 'Cache-Control': 'public' };
