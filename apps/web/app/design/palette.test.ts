import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"

import { DATA_CATEGORICAL, NEUTRAL, oklchToHex } from "./palette"

const css = readFileSync(
  fileURLToPath(new URL("../app.css", import.meta.url)),
  "utf8"
)
const rootBlock = css.slice(css.indexOf(":root {"), css.indexOf("@layer base"))
const tokens = [...rootBlock.matchAll(/--([\w-]+):\s*([^;]+);/g)].map(
  ([, name, value]) => ({ name, value: value.trim() })
)

describe("디자인 원칙: 색상은 데이터에만 쓴다", () => {
  it("UI 토큰은 채도 0 이다", () => {
    const ui = tokens.filter(
      (t) => !t.name.startsWith("data-") && !t.name.startsWith("chart-") && t.name !== "radius"
    )
    expect(ui.length).toBeGreaterThan(20)
    for (const t of ui) {
      expect(t.value, t.name).toMatch(/^oklch\([\d.]+ 0 0( \/ \d+%)?\)$/)
    }
  })

  it("chart 토큰은 데이터 팔레트를 가리킨다", () => {
    const charts = tokens.filter((t) => t.name.startsWith("chart-"))
    expect(charts).toHaveLength(5)
    for (const t of charts) expect(t.value).toMatch(/^var\(--data-cat-\d\)$/)
  })

  it("CSS 데이터 팔레트와 palette.ts 가 같다", () => {
    DATA_CATEGORICAL.forEach(([l, c, h], i) => {
      const t = tokens.find((x) => x.name === `data-cat-${i + 1}`)
      expect(t?.value).toBe(`oklch(${l} ${c} ${h})`)
    })
  })

  it("3D 장면의 무채색 값은 R=G=B 이다", () => {
    for (const [name, hex] of Object.entries(NEUTRAL)) {
      const [r, g, b] = [1, 3, 5].map((i) => hex.slice(i, i + 2))
      expect(r === g && g === b, name).toBe(true)
    }
  })

  it("OKLCH 변환은 무채색 입력에 회색을 낸다", () => {
    expect(oklchToHex([1, 0, 0])).toBe("#ffffff")
    expect(oklchToHex([0, 0, 0])).toBe("#000000")
  })
})
