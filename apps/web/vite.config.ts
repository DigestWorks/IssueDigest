import { reactRouter } from "@react-router/dev/vite"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"

export default defineConfig({
  resolve: { tsconfigPaths: true },
  plugins: [tailwindcss(), reactRouter()],
  // 스테이지는 지연 로딩되므로 개발 서버가 의존성을 늦게 발견해 React 사본이
  // 둘로 나뉠 수 있다. 시작 시 미리 번들한다.
  optimizeDeps: {
    include: [
      "three",
      "@react-three/fiber",
      "@react-three/drei",
      "@react-three/postprocessing",
      "postprocessing",
      "d3-force-3d",
      "d3-geo",
      "zustand",
      "zod",
      "motion/react",
    ],
  },
})
