import { createContext, useContext } from "react"
import { Color } from "three"

import type { SchematicPalette } from "~/design/tokens"

/** 장면 색(SCHEMATIC_THEMES 의 한 모드). Canvas 안에서 제공하므로 R3F 의 컨텍스트 연결 여부와 관계없이 읽힌다 */
export const ThemeContext = createContext<SchematicPalette | null>(null)

export const useTheme = () => {
  const t = useContext(ThemeContext)
  if (!t) throw new Error("장면 밖에서 테마를 읽었습니다(ThemeContext.Provider 필요)")
  return t
}

/** 어두운 장면인지(바탕 명도 기준) */
export const isDarkTheme = (th: SchematicPalette) => new Color(th.scene).getHSL({ h: 0, s: 0, l: 0 }).l < 0.5
