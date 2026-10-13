import { MainScreen } from "~/main/main-screen"

import type { Route } from "./+types/main"

export function meta(_: Route.MetaArgs) {
  return [
    { title: "IssueDigest" },
    { name: "description", content: "한국 사회 데이터를 조사하고 출처와 함께 시각 기록으로 보여 주는 프로토타입" },
  ]
}

export default function Main() {
  return <MainScreen />
}
