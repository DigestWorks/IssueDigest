import type { ReactNode } from "react"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "~/components/ui/card"
import type { Source } from "../events"

/** 결과 패널의 공통 틀. 반투명 무채색 카드와 출처 줄. */
export function PanelCard({
  eyebrow,
  title,
  source,
  children,
}: {
  eyebrow: string
  title: string
  source?: Source
  children: ReactNode
}) {
  return (
    <Card size="sm" className="bg-card/70 shadow-[0_18px_40px_-18px_rgb(0_0_0/0.22)] backdrop-blur-md">
      <CardHeader>
        <CardDescription className="text-[11px] tracking-[0.12em]">{eyebrow}</CardDescription>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
      {source ? (
        <CardFooter className="text-[11px] text-muted-foreground">
          출처: {source.label}
          {source.span ? ` · ${source.span}` : ""}
        </CardFooter>
      ) : null}
    </Card>
  )
}
