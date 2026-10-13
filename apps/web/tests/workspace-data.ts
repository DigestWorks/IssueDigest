// Synthetic HTTP responses only; never imported by the application.
export const workspace = '00000000-0000-4000-8000-000000000001';
export const otherWorkspace = '00000000-0000-4000-8000-000000000002';
export const snapshot = '00000000-0000-4000-8000-000000000099';
export const requestId = '8ff9af27-d021-4fb3-a46e-cf8c3d093c44';
export const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Request-ID': requestId };
export const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers });
export const session = () => ({ schema_version: 1, user_id: snapshot, memberships: [{ workspace_id: workspace, role: 'viewer' }, { workspace_id: otherWorkspace, role: 'editor' }] });
export const catalog = (id = workspace) => ({ schema_version: 1, workspace_id: id, items: [{ snapshot_id: snapshot, document_id: snapshot, provider: '합성 공급처', source_id: 'synthetic-source', source_kind: 'other', canonical_url: null, collected_at: '2026-10-13T00:00:00Z', excerpt: id === workspace ? '첫 공간 합성 원문' : '두 번째 공간 합성 원문', citation_count: 3 }], has_more: false });
