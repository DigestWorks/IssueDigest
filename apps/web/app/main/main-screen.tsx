import { useSearchParams } from "react-router"

import type { SchematicMode } from "~/design/tokens"
import { SchematicTheme } from "~/stage/schematic/primitives"
import { ResearchLog } from "./log/research-log"
import { MainStage } from "./stage/main-stage"

/**
 * 메인 화면: 왼쪽 대화 열(조사 기록)과 오른쪽 3D 스테이지.
 * 어두운 모드가 기본이고 대화 열의 전환 버튼이나 ?mode=light 로 밝은 모드를 쓴다.
 */
export function MainScreen() {
  const [params, setParams] = useSearchParams()
  const mode: SchematicMode = params.get("mode") === "light" ? "light" : "dark"
  const setMode = (m: SchematicMode) => setParams(m === "dark" ? {} : { mode: m }, { replace: true, preventScrollReset: true })

  return (
    <SchematicTheme mode={mode} className="grid h-svh grid-cols-[400px_minmax(0,1fr)] overflow-hidden" style={{ background: "var(--sch-scene)" }}>
      <ResearchLog mode={mode} onMode={setMode} />
      <MainStage mode={mode} />
    </SchematicTheme>
  )
}
