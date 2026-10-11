import type { ReactNode } from "react"

import { Badge } from "~/components/ui/badge"
import { Separator } from "~/components/ui/separator"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table"
import { CHAPTERS, IDENTITY, statusCounts, type RuleStatus } from "~/design/guide"
import { SCENARIOS } from "~/stage/scenarios"
import { electionMapScenario } from "~/stage/scenarios/election-map"
import {
  DataPaletteSpecimen,
  GlyphSpecimen,
  LineSpecimen,
  MotionSpecimen,
  OpacitySpecimen,
  SchematicMapSpecimen,
  SchematicPanelSpecimen,
  TiltSpecimen,
  TypeSpecimen,
  UiColorSpecimen,
} from "~/style/specimens"

import type { Route } from "./+types/style"

export function meta(_: Route.MetaArgs) {
  return [{ title: "스타일 가이드 · IssueDigest" }]
}

/** 장별 견본. 규칙 표 아래에 실제 코드의 토큰과 컴포넌트로 그린다. */
const SPECIMENS: Record<string, { title: string; node: ReactNode }[]> = {
  ingredients: [
    { title: "노드 기호", node: <GlyphSpecimen /> },
    { title: "선 종류", node: <LineSpecimen /> },
  ],
  color: [
    { title: "UI 색 토큰 (채도 0)", node: <UiColorSpecimen /> },
    { title: "데이터 팔레트", node: <DataPaletteSpecimen /> },
    { title: "불투명도 단계", node: <OpacitySpecimen /> },
  ],
  type: [
    { title: "글자 역할", node: <TypeSpecimen /> },
    { title: "35° 규칙", node: <TiltSpecimen /> },
  ],
  motion: [{ title: "등장 순서", node: <MotionSpecimen /> }],
}

const SAMPLE_PANELS = SCENARIOS.flatMap((s) =>
  s.steps.flatMap((st) => ("event" in st && st.event.type === "panel.add" ? [st.event.panel] : []))
)
SPECIMENS.panels = [{ title: "결과 패널 (시나리오 샘플 데이터)", node: <SchematicPanelSpecimen panels={SAMPLE_PANELS} /> }]

/** 지도 견본에서 색으로 표시할 도심 자치구: 종로·중·용산·성동·동대문·서대문 */
const CENTRAL_GU = ["11010", "11020", "11030", "11040", "11060", "11130"]
const mapEvents = electionMapScenario.steps.flatMap((st) => ("event" in st ? [st.event] : []))
const mapShow = mapEvents.find((e) => e.type === "map.show")
const mapValues = mapEvents.find((e) => e.type === "map.choropleth")
if (mapShow?.type === "map.show" && mapValues?.type === "map.choropleth") {
  SPECIMENS.map = [
    {
      title: "3D 지도 (지도 시나리오 샘플 데이터)",
      node: (
        <SchematicMapSpecimen
          data={{
            title: mapShow.title,
            values: mapValues.values,
            colored: CENTRAL_GU,
            legend: mapValues.legend,
            source: mapValues.source,
          }}
        />
      ),
    },
  ]
}

const STATUS_VARIANT: Record<RuleStatus, "default" | "secondary" | "outline"> = {
  구현: "default",
  부분: "secondary",
  미구현: "outline",
}

export default function StyleGuide() {
  const counts = statusCounts()
  return (
    <div className="min-h-svh bg-background">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-6 py-12 lg:grid-cols-[200px_minmax(0,1fr)]">
        <nav className="hidden lg:block">
          <div className="sticky top-12 flex flex-col gap-1 text-sm">
            <a href="#identity" className="py-1 text-muted-foreground hover:text-foreground">
              0. 정체성
            </a>
            {CHAPTERS.map((c) => (
              <a key={c.id} href={`#${c.id}`} className="py-1 text-muted-foreground hover:text-foreground">
                {c.number}. {c.title}
              </a>
            ))}
            <Separator className="my-3" />
            <a href="/" className="py-1 text-muted-foreground hover:text-foreground">
              스테이지로 돌아가기
            </a>
          </div>
        </nav>

        <main className="flex min-w-0 flex-col gap-16">
          <header id="identity" className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
              <span className="text-xs tracking-[0.2em] text-muted-foreground uppercase">IssueDigest · Style Guide v0.1</span>
              <h1 className="text-4xl font-light tracking-[0.02em]">{IDENTITY.name}</h1>
            </div>
            <p className="max-w-3xl text-[15px] leading-relaxed text-foreground/80">{IDENTITY.statement}</p>
            <ol className="grid max-w-4xl grid-cols-1 gap-3 sm:grid-cols-2">
              {IDENTITY.consequences.map((c, i) => (
                <li key={i} className="flex gap-3 rounded-lg border border-border p-4 text-sm leading-relaxed">
                  <span className="font-mono text-xs text-muted-foreground tabular-nums">{String(i + 1).padStart(2, "0")}</span>
                  {c}
                </li>
              ))}
            </ol>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              규칙 구현 상태
              {(Object.keys(counts) as RuleStatus[]).map((k) => (
                <Badge key={k} variant={STATUS_VARIANT[k]}>
                  {k} {counts[k]}
                </Badge>
              ))}
            </div>
          </header>

          {CHAPTERS.map((c) => (
            <section key={c.id} id={c.id} className="flex scroll-mt-12 flex-col gap-6">
              <div className="flex items-baseline gap-4">
                <span className="font-mono text-sm text-muted-foreground tabular-nums">{String(c.number).padStart(2, "0")}</span>
                <h2 className="text-2xl font-light">{c.title}</h2>
                <span className="text-sm text-muted-foreground">{c.summary}</span>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-36">규칙</TableHead>
                    <TableHead>내용</TableHead>
                    <TableHead className="w-20">상태</TableHead>
                    <TableHead className="w-64">구현 위치</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {c.rules.map((r) => (
                    <TableRow key={r.title}>
                      <TableCell className="align-top font-medium">{r.title}</TableCell>
                      <TableCell className="align-top whitespace-normal leading-relaxed">{r.rule}</TableCell>
                      <TableCell className="align-top">
                        <Badge variant={STATUS_VARIANT[r.status]}>{r.status}</Badge>
                      </TableCell>
                      <TableCell className="align-top font-mono text-[11px] whitespace-normal text-muted-foreground">{r.where}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {SPECIMENS[c.id]?.map((sp) => (
                <div key={sp.title} className="flex flex-col gap-4 rounded-xl border border-border p-6">
                  <h3 className="text-xs tracking-[0.14em] text-muted-foreground">{sp.title}</h3>
                  {sp.node}
                </div>
              ))}
            </section>
          ))}

        </main>
      </div>
    </div>
  )
}

