import { useState } from "react"
import { useSearchParams } from "react-router"

import type { SchematicMode } from "~/design/tokens"
import { ControlButton, op } from "~/stage/schematic/primitives"
import { SchematicMap } from "~/stage/schematic/map/schematic-map"
import { electionMapSample } from "~/stage/scenarios/election-map"

import type { Route } from "./+types/map"

export function meta(_: Route.MetaArgs) {
  return [{ title: "지도 · IssueDigest" }]
}

const SAMPLE = electionMapSample()

/** 3D 지도만 화면 전체에 띄운 페이지(지도 시나리오 샘플 데이터). ?mode=light 로 밝은 모드를 연다. */
export default function MapPage() {
  const [params, setParams] = useSearchParams()
  const mode: SchematicMode = params.get("mode") === "light" ? "light" : "dark"
  const [run, setRun] = useState(0)
  const [focus, setFocus] = useState<string | null>(null)

  const replay = () => {
    setFocus(null)
    setRun((r) => r + 1)
  }
  const setMode = (m: SchematicMode) =>
    setParams(m === "dark" ? {} : { mode: m }, { replace: true, preventScrollReset: true })

  return (
    <main className="h-svh w-full">
      <SchematicMap
        key={run}
        {...SAMPLE}
        mode={mode}
        focus={focus}
        onFocus={setFocus}
        className="h-full w-full"
        controls={
          <>
            <span className="mt-3 mb-1 font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("context") }}>
              화면
            </span>
            <ControlButton active={false} onClick={replay}>
              다시 재생
            </ControlButton>
            <ControlButton active={mode === "dark"} onClick={() => setMode("dark")}>
              다크
            </ControlButton>
            <ControlButton active={mode === "light"} onClick={() => setMode("light")}>
              라이트
            </ControlButton>
          </>
        }
      />
    </main>
  )
}
