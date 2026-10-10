import { type RouteConfig, index, route } from "@react-router/dev/routes"

export default [index("routes/home.tsx"), route("style", "routes/style.tsx")] satisfies RouteConfig
