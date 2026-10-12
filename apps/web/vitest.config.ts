import { defineConfig } from "vitest/config"

// vite.config.ts 의 reactRouter 플러그인은 테스트 환경에서 쓰지 않는다.
export default defineConfig({
  resolve: { tsconfigPaths: true },
  test: { include: ["app/**/*.test.ts"] },
})
