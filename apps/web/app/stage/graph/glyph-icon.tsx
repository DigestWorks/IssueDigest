import { cn } from "~/lib/utils"
import { glyphPoints, NODE_GLYPH, type NodeType } from "./glyphs"

/** 노드 기호의 SVG 판. 범례와 /style 페이지가 장면과 같은 기호 정의를 쓴다. */
export function GlyphIcon({ type, className }: { type: NodeType; className?: string }) {
  const g = NODE_GLYPH[type]
  const points = glyphPoints(g, 5)
    .map(([x, y]) => `${6 + x},${6 - y}`)
    .join(" ")
  return (
    <svg viewBox="0 0 12 12" className={cn("size-3", className)} aria-hidden>
      <polygon
        points={points}
        className={g.filled ? "fill-foreground" : "fill-none stroke-foreground"}
        strokeWidth={1.2}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
