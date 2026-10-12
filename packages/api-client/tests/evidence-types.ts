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

export type AuthenticationErrorIsGenerated = Assert<Equal<
  Operation['responses'][401]['content']['application/json'], components['schemas']['EvidenceAuthenticationError']
>>;
export type MissingErrorIsGenerated = Assert<Equal<
  Operation['responses'][404]['content']['application/json'], components['schemas']['EvidenceNotFoundError']
>>;
export type ValidationErrorIsGenerated = Assert<Equal<
  Operation['responses'][422]['content']['application/json'], components['schemas']['EvidencePathValidationError']
>>;
export type UnavailableErrorIsGenerated = Assert<Equal<
  Operation['responses'][503]['content']['application/json'], components['schemas']['EvidenceUnavailableError']
>>;
export const authenticationError: Operation['responses'][401]['content']['application/json'] = {
  detail: 'Authentication required',
};
export const missingError: Operation['responses'][404]['content']['application/json'] = {
  detail: 'Evidence not found',
};
export const validationError: Operation['responses'][422]['content']['application/json'] = {
  detail: [{ type: 'uuid_parsing', loc: ['path', 'workspace_id'], msg: 'Invalid UUID4 path parameter' }],
};
export const unavailableError: Operation['responses'][503]['content']['application/json'] = {
  detail: 'Evidence service unavailable',
};
// @ts-expect-error failure body exposes only the fixed unavailable detail
export const privateFailure: Operation['responses'][503]['content']['application/json'] = { detail: 'raw private exception' };
// @ts-expect-error validation errors cannot echo source or token input
export const echoedValidation: Operation['responses'][422]['content']['application/json'] = { detail: [{ type: 'uuid_parsing', loc: ['path', 'workspace_id'], msg: 'Invalid UUID4 path parameter', input: 'untrusted input' }] };
