import { index, route, type RouteConfig } from '@react-router/dev/routes';
export default [index('routes/home.tsx'), route('workspaces/:workspaceId/evidence/:snapshotId', 'routes/evidence.tsx')] satisfies RouteConfig;
