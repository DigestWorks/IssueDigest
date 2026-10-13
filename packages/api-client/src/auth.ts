import type { components } from './schema';
import { hasKeys, isId, isObject, protectedRequest, type ProtectedFailure, type ProtectedOptions } from './protected-request';

export type SessionInfo = components['schemas']['SessionInfo'];
export type WorkspaceMembership = components['schemas']['WorkspaceMembership'];
export type AuthFailure = ProtectedFailure;
export type AuthOptions = ProtectedOptions;
export class AuthError extends Error {
  constructor(public readonly kind: AuthFailure, public readonly requestId?: string) {
    super(`Authentication request failed: ${kind}`); this.name = 'AuthError';
  }
}
function isSession(value: unknown): value is SessionInfo {
  if (!isObject(value) || !hasKeys(value, ['schema_version', 'user_id', 'memberships']) || value.schema_version !== 1 || !isId(value.user_id) || !Array.isArray(value.memberships) || value.memberships.length > 100) return false;
  let previous = '';
  for (const membership of value.memberships) {
    if (!isObject(membership) || !hasKeys(membership, ['workspace_id', 'role']) || !isId(membership.workspace_id) || typeof membership.role !== 'string' || !['viewer', 'editor', 'owner'].includes(membership.role)) return false;
    const id = membership.workspace_id.toLowerCase();
    if (id <= previous) return false;
    previous = id;
  }
  return true;
}
const error = (kind: AuthFailure, requestId?: string) => new AuthError(kind, requestId);
export function getSession(options: AuthOptions = {}): Promise<{ data: SessionInfo; requestId: string }> {
  return protectedRequest('/api/v1/auth/session', 'GET', isSession, error, options);
}
/** Browser supplies the same-origin Origin header; no credential is exposed to JS. */
export async function logout(options: AuthOptions = {}): Promise<{ requestId: string }> {
  const result = await protectedRequest('/api/v1/auth/logout', 'POST', (data): data is undefined => data === undefined, error, options);
  return { requestId: result.requestId };
}
