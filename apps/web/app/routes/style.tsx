import type { ReactNode } from "react"
import { useSearchParams } from "react-router"

import { CHAPTERS, IDENTITY, RETIRED, statusCounts, type RuleStatus } from "~/design/guide"
import type { SchematicMode } from "~/design/tokens"
import { ACCENT, ControlButton, INK, op, Rule, SchematicTheme, SquarePoint } from "~/stage/schematic/primitives"
import { SCENARIOS } from "~/stage/scenarios"
import { electionMapSample } from "~/stage/scenarios/election-map"
import {
  AccentSpecimen,
  AnnotationSpecimen,
  CalloutSpecimen,
  ColorScopeSpecimen,
  DataPaletteSpecimen,
  FringeSpecimen,
  HudSpecimen,
  LayerSpecimen,
  MotionSpecimen,
  OpacitySpecimen,
  SceneSpecimen,
  SchematicMapSpecimen,
  SchematicPanelSpecimen,
  TypeSpecimen,
} from "~/style/specimens"

import type { Route } from "./+types/style"

export function meta(_: Route.MetaArgs) {
  return [{ title: "스타일 가이드 · IssueDigest" }]
}

const SAMPLE_PANELS = SCENARIOS.flatMap((s) =>
  s.steps.flatMap((st) => ("event" in st && st.event.type === "panel.add" ? [st.event.panel] : []))
)

/** 장별 견본. 규칙 목록 아래에 실제 토큰과 컴포넌트로 그린다. */
const SPECIMENS: Record<string, { title: string; node: ReactNode }[]> = {
  scene: [{ title: "장면 값과 바닥 조명", node: <SceneSpecimen /> }],
  lines: [
    { title: "불투명도 단계", node: <OpacitySpecimen /> },
    { title: "측정 주석", node: <AnnotationSpecimen /> },
    { title: "지시선과 주석", node: <CalloutSpecimen /> },
  ],
  color: [
    { title: "데이터 색 범위", node: <ColorScopeSpecimen /> },
    { title: "데이터 팔레트", node: <DataPaletteSpecimen /> },
    { title: "주황", node: <AccentSpecimen /> },
  ],
  volume: [{ title: "층 묶음과 선택 시 확장", node: <LayerSpecimen /> }],
  effects: [{ title: "층 색 번짐", node: <FringeSpecimen /> }],
  type: [{ title: "머리 줄과 글자 역할", node: <TypeSpecimen /> }],
  hud: [{ title: "화면 고정 주석 요소", node: <HudSpecimen /> }],
  panels: [{ title: "결과 패널 · 시나리오 샘플 데이터", node: <SchematicPanelSpecimen panels={SAMPLE_PANELS} /> }],
  map: [{ title: "3D 지도 · 지도 시나리오 샘플 데이터", node: <SchematicMapSpecimen data={electionMapSample()} /> }],
  motion: [{ title: "점 → 선 → 글자", node: <MotionSpecimen /> }],
}

const hairline = `color-mix(in oklab, ${INK} 11%, transparent)`
const pad = (n: number) => String(n).padStart(2, "0")

/** 구현 상태 표시: 구현은 채운 사각점, 부분은 빈 사각점, 미구현은 옅은 빈 사각점 */
function StatusMark({ status }: { status: RuleStatus }) {
  return (
    <span className="flex items-center gap-0.5 font-mono text-[10px] tracking-[0.12em]" style={{ opacity: status === "미구현" ? op("context") : 1 }}>
      <SquarePoint size={5} filled={status === "구현"} />
      <span style={{ opacity: status === "구현" ? 1 : op("related") }}>{status}</span>
    </span>
  )
}

/** 장 머리: 「번호 | 요약」 줄, 제목, 머리선 */
function SectionHead({ index, caption, title }: { index: string; caption: string; title: string }) {
  return (
    <header className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2 text-[10px] tracking-[0.22em]" style={{ opacity: op("related") }}>
        <span className="font-mono tabular-nums">{index}</span>
        <span className="h-2.5 w-px" style={{ background: INK }} />
        <span>{caption}</span>
      </div>
      <h2 className="text-[26px] leading-tight font-extralight tracking-[0.06em]" style={{ opacity: 0.92, textShadow: "0 1px 0 var(--sch-shadow)" }}>
        {title}
      </h2>
      <Rule animate={false} />
    </header>
  )
}

/** 도면 양식 색 모드 전환. ?mode=light 로도 연다 */
function ModeSwitch({ mode, onChange }: { mode: SchematicMode; onChange: (m: SchematicMode) => void }) {
  return (
    <div className="flex items-center gap-4">
      {(["dark", "light"] as const).map((m) => (
        <ControlButton key={m} active={mode === m} onClick={() => onChange(m)} point="start">
          {m === "dark" ? "다크" : "라이트"}
        </ControlButton>
      ))}
    </div>
  )
}

/**
 * 스타일 가이드. 규칙 데이터(design/guide.ts)와 견본(style/specimens.tsx)을 도면 양식으로 렌더링한다.
 * 어두운 모드가 기본이고 ?mode=light 또는 전환 버튼으로 밝은 모드를 본다.
 */
export default function StyleGuide() {
  const counts = statusCounts()
  const [params, setParams] = useSearchParams()
  const mode: SchematicMode = params.get("mode") === "light" ? "light" : "dark"
  const setMode = (m: SchematicMode) => setParams(m === "dark" ? {} : { mode: m }, { replace: true, preventScrollReset: true })

  return (
    <SchematicTheme mode={mode} className="min-h-svh" style={{ background: "var(--sch-scene)" }}>
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 px-6 py-12 lg:grid-cols-[200px_minmax(0,1fr)]">
        {/* 목차 */}
        <nav className="hidden lg:block">
          <div className="sticky top-12 flex flex-col gap-4">
            <span className="font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("related") }}>
              ISSUEDIGEST · 스타일
            </span>
            <ol className="flex flex-col gap-1.5 text-[12px] tracking-[0.04em]">
              <li>
                <a href="#identity" className="flex gap-2 hover:opacity-100" style={{ opacity: op("related") }}>
                  <span className="font-mono tabular-nums">00</span>
                  정체성
                </a>
              </li>
              {CHAPTERS.map((c) => (
                <li key={c.id}>
                  <a href={`#${c.id}`} className="flex gap-2 hover:opacity-100" style={{ opacity: op("related") }}>
                    <span className="font-mono tabular-nums">{pad(c.number)}</span>
                    {c.title}
                  </a>
                </li>
              ))}
              <li>
                <a href="#retired" className="flex gap-2 hover:opacity-100" style={{ opacity: op("context") }}>
                  <span className="font-mono tabular-nums">··</span>
                  폐기한 규칙
                </a>
              </li>
            </ol>
            <span className="h-px w-full" style={{ background: hairline }} />
            <span className="font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("context") }}>
              색 모드
            </span>
            <ModeSwitch mode={mode} onChange={setMode} />
            <span className="h-px w-full" style={{ background: hairline }} />
            <a href="/map" className="text-[12px] tracking-[0.04em]" style={{ opacity: op("related") }}>
              지도 페이지
            </a>
            <a href="/" className="text-[12px] tracking-[0.04em]" style={{ opacity: op("related") }}>
              스테이지로 돌아가기
            </a>
          </div>
        </nav>

        <main className="flex min-w-0 flex-col gap-20">
          {/* 정체성 */}
          <section id="identity" className="flex scroll-mt-12 flex-col gap-6">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("related") }}>
                <span>스타일 가이드 v0.2</span>
                <span className="h-2.5 w-px" style={{ background: INK }} />
                <span>2026-10-11 지도 기준 재정의</span>
              </div>
              <div className="lg:hidden">
                <ModeSwitch mode={mode} onChange={setMode} />
              </div>
            </div>
            <h1 className="text-[40px] leading-tight font-extralight tracking-[0.04em]" style={{ textShadow: "0 1px 0 var(--sch-shadow)" }}>
              {IDENTITY.name}
            </h1>
            <Rule animate={false} />
            <p className="max-w-3xl text-[15px] leading-relaxed tracking-[0.01em]" style={{ opacity: 0.85 }}>
              {IDENTITY.statement}
            </p>
            <ol className="grid max-w-4xl grid-cols-1 gap-x-10 gap-y-4 sm:grid-cols-2">
              {IDENTITY.consequences.map((c, i) => (
                <li key={i} className="flex gap-3 border-l pl-3 text-[13px] leading-relaxed" style={{ borderColor: hairline }}>
                  <span className="font-mono text-[10px] tabular-nums" style={{ opacity: op("related") }}>
                    {pad(i + 1)}
                  </span>
                  <span style={{ opacity: 0.85 }}>{c}</span>
                </li>
              ))}
            </ol>
            <div className="flex flex-wrap items-center gap-5">
              <span className="font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("context") }}>
                규칙 구현 상태
              </span>
              {(Object.keys(counts) as RuleStatus[]).map((k) => (
                <span key={k} className="flex items-center gap-1">
                  <StatusMark status={k} />
                  <span className="font-mono text-[10px] tabular-nums">{counts[k]}</span>
                </span>
              ))}
            </div>
          </section>

          {/* 장 */}
          {CHAPTERS.map((c) => (
            <section key={c.id} id={c.id} className="flex scroll-mt-12 flex-col gap-8">
              <SectionHead index={pad(c.number)} caption={c.summary} title={c.title} />
              <ol className="flex flex-col">
                {c.rules.map((r) => (
                  <li
                    key={r.title}
                    className="grid grid-cols-1 gap-x-6 gap-y-1.5 border-t py-4 md:grid-cols-[140px_minmax(0,1fr)_200px]"
                    style={{ borderColor: hairline }}
                  >
                    <span className="text-[13px] font-medium tracking-[0.02em]">{r.title}</span>
                    <span className="text-[13px] leading-relaxed" style={{ opacity: 0.85 }}>
                      {r.rule}
                    </span>
                    <div className="flex flex-col gap-1">
                      <StatusMark status={r.status} />
                      <span className="font-mono text-[10px] leading-snug break-words" style={{ opacity: op("context") }}>
                        {r.where}
                      </span>
                    </div>
                  </li>
                ))}
              </ol>
              {SPECIMENS[c.id]?.map((sp) => (
                <div key={sp.title} className="flex flex-col gap-4">
                  <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("related") }}>
                    <span className="size-[4px]" style={{ background: ACCENT }} />
                    <span>견본</span>
                    <span className="h-2.5 w-px" style={{ background: INK }} />
                    <span>{sp.title}</span>
                  </div>
                  {sp.node}
                </div>
              ))}
            </section>
          ))}

          {/* 폐기한 규칙 */}
          <section id="retired" className="flex scroll-mt-12 flex-col gap-8">
            <SectionHead index="··" caption="지도 기준 재정의로 바뀐 규칙" title="폐기한 규칙" />
            <ol className="flex flex-col">
              {RETIRED.map((r) => (
                <li
                  key={r.rule}
                  className="grid grid-cols-1 gap-x-6 gap-y-1.5 border-t py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_200px]"
                  style={{ borderColor: hairline }}
                >
                  <span className="text-[13px] leading-relaxed line-through" style={{ opacity: op("related") }}>
                    {r.rule}
                  </span>
                  <span className="text-[13px] leading-relaxed" style={{ opacity: 0.85 }}>
                    {r.reason}
                  </span>
                  <span className="font-mono text-[10px] leading-snug" style={{ opacity: r.replacedBy ? op("related") : op("context") }}>
                    {r.replacedBy ? `→ ${r.replacedBy}` : "→ 홈 스테이지 적용 때 재정의"}
                  </span>
                </li>
              ))}
            </ol>
          </section>
        </main>
      </div>
    </SchematicTheme>
  )
}
