import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "~/components/ui/chart"
import { dataColor } from "~/design/palette"
import type { Panel } from "../events"
import { PanelCard } from "./panel-card"

type ChartPanelData = Extract<Panel, { kind: "chart" }>

/** 계열 색은 데이터 팔레트, 축과 격자는 무채색이다. 선은 왼쪽에서 오른쪽으로 그려지며 나타난다. */
export function ChartPanel({ panel, animate }: { panel: ChartPanelData; animate: boolean }) {
  const config = Object.fromEntries(
    panel.series.map((s) => [s.key, { label: s.label, color: dataColor(s.category) }])
  ) satisfies ChartConfig

  return (
    <PanelCard eyebrow={`차트 · 단위 ${panel.unit}`} title={panel.title} source={panel.source}>
      <ChartContainer config={config} className="aspect-[5/2] w-full">
        <LineChart data={panel.rows} margin={{ left: 0, right: 8, top: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey={panel.xKey} tickLine={false} axisLine={false} tickMargin={8} />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={40}
            tickFormatter={(v: number) => new Intl.NumberFormat("ko-KR", { notation: "compact" }).format(v)}
          />
          <ChartTooltip content={<ChartTooltipContent />} />
          {panel.series.map((s, i) => (
            <Line
              key={s.key}
              dataKey={s.key}
              type="monotone"
              stroke={`var(--color-${s.key})`}
              strokeWidth={2}
              dot={false}
              isAnimationActive={animate}
              animationBegin={300 + i * 250}
              animationDuration={1400}
            />
          ))}
        </LineChart>
      </ChartContainer>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
        {panel.series.map((s) => (
          <span key={s.key} className="flex items-center gap-1.5">
            <span className="h-0.5 w-3 rounded-full" style={{ backgroundColor: dataColor(s.category) }} />
            {s.label}
          </span>
        ))}
      </div>
    </PanelCard>
  )
}
