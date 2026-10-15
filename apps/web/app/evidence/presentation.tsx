import type { ReactNode } from 'react';

const sourceKinds = {
  bill: '법안', legal_text: '법령', government_document: '정부 문서', news: '기사',
  poll: '여론조사', statistics: '통계', petition: '청원', other: '기타 자료',
} as const;

export function sourceKind(kind: keyof typeof sourceKinds) { return sourceKinds[kind]; }

export function CollectedDate({ value }: { value: string }) {
  return <time dateTime={value}>수집 {new Intl.DateTimeFormat('ko-KR', { timeZone: 'UTC', year: 'numeric', month: 'numeric', day: 'numeric' }).format(new Date(value))}</time>;
}

export function TechnicalDetails({ children }: { children: ReactNode }) {
  return <details className="technical-details"><summary>자세한 정보</summary><div>{children}</div></details>;
}
