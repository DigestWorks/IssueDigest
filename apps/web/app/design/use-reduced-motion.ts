import { useSyncExternalStore } from "react"

const QUERY = "(prefers-reduced-motion: reduce)"

const subscribe = (onChange: () => void) => {
  const mql = window.matchMedia(QUERY)
  mql.addEventListener("change", onChange)
  return () => mql.removeEventListener("change", onChange)
}

/** 운영체제의 동작 줄이기 설정. 켜져 있으면 애니메이션과 효과를 줄인다. */
export function useReducedMotion() {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => false
  )
}

export const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia(QUERY).matches
