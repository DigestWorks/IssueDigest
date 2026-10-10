import type { Config } from "@react-router/dev/config"

// SPA 모드. 루트 라우트는 빌드 시 index.html 로 미리 렌더되므로
// three.js 처럼 브라우저 전용 코드는 클라이언트에서만 불러온다.
export default {
  ssr: false,
} satisfies Config
