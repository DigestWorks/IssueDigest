import type { CanvasAction, Claim, Relation } from '@issuedigest/api-client';
import type { CitationDisplay, DisplayContext } from './prepare';

export type ActionHandler = ((action: CanvasAction) => void) | undefined;
const bases: Record<Claim['basis'], string> = {
  source_assertion: '원문 주장', observation: '관측', inference: '추론',
};
export const predicates: Record<Relation['predicate'], string> = {
  introduced_by: '발의자', reviewed_by: '심사 주체', alternative_to: '대안 관계',
  supports: '지지', contradicts: '상충', mentions: '언급',
};
export function Basis({value, aiGenerated}: {value: Claim['basis']; aiGenerated?: boolean}) {
  return <span className="id-canvas-basis">{aiGenerated && value === 'inference' ? 'AI 해석' : bases[value]}</span>;
}
export function sourceTitle(documentId: string, context: DisplayContext, titles?: Record<string, string>) {
  return titles?.[documentId] ?? context.documents.get(documentId)!.source_id;
}
export function speaker(claim: Claim, context: DisplayContext, titles?: Record<string, string>) {
  if (claim.basis === 'inference' && titles && claim.speaker_entity_id === null) {
    const names = [...new Set(claim.citation_ids.map(id => sourceTitle(context.citations.get(id)!.proof.document.document_id, context, titles)))];
    return names.join(' · ');
  }
  return claim.speaker_entity_id === null ? '발화 주체 미제공' : context.entities.get(claim.speaker_entity_id)!.name;
}
export function endpointText(value: Relation['source'], context: DisplayContext): string {
  switch (value.kind) {
    case 'entity': return context.entities.get(value.entity_id)!.name;
    case 'claim': return context.claims.get(value.claim_id)!.text;
    case 'document': return context.documents.get(value.document_id)!.source_id;
  }
}
function location({citation}: CitationDisplay) {
  const selector = citation.selector;
  switch (selector.kind) {
    case 'text': return `텍스트 · 문자 ${selector.start}–${selector.end}`;
    case 'pdf': return `페이지 ${selector.page_number} · 문자 ${selector.start}–${selector.end}`;
    case 'table_cell': return `표 ${selector.table_id} · 셀 ${selector.cell_id}`;
  }
}
function actionLabel(action: CanvasAction, context: DisplayContext, titles?: Record<string, string>) {
  switch (action.kind) {
    case 'open_evidence': {
      const display = context.citations.get(action.citation_id)!;
      return `근거 열기: ${sourceTitle(display.proof.document.document_id, context, titles)} · ${location(display)}`;
    }
    case 'select_document': return `문서 선택: ${sourceTitle(action.document_id, context, titles)}`;
    case 'ask_question': return `후속 질문: ${action.question}`;
    case 'sort': return `정렬: ${action.field === 'title' ? '제목' : '자료 날짜'} · ${action.direction === 'asc' ? '오름차순' : '내림차순'}`;
  }
}
export function ActionButton({action, context, sourceTitles, onAction}: {
  action: CanvasAction; context: DisplayContext; sourceTitles?: Record<string, string>; onAction: ActionHandler;
}) {
  const label = actionLabel(action, context, sourceTitles);
  const compactCitation = Boolean(sourceTitles) && action.kind === 'open_evidence';
  return <button type="button" disabled={!onAction} onClick={() => onAction?.(action)} aria-label={compactCitation ? label : undefined} title={compactCitation ? label : undefined}>{compactCitation ? '근거 열기' : label}</button>;
}
export function EvidenceCard({display, context, sourceTitles, onAction}: {
  display: CitationDisplay; context: DisplayContext; sourceTitles?: Record<string, string>; onAction: ActionHandler;
}) {
  return <figure className="id-canvas-evidence">
    <figcaption><strong>{sourceTitle(display.proof.document.document_id, context, sourceTitles)}</strong><span>{location(display)}</span></figcaption>
    <blockquote>{display.citation.selector.quote}</blockquote>
    <ActionButton action={{kind: 'open_evidence', citation_id: display.citation.citation_id}} context={context} sourceTitles={sourceTitles} onAction={onAction} />
  </figure>;
}
export function EvidenceLinks({ids, context, sourceTitles, onAction}: {
  ids: string[]; context: DisplayContext; sourceTitles?: Record<string, string>; onAction: ActionHandler;
}) {
  return <div className="id-canvas-evidence-links">{ids.map(id => <ActionButton key={id} action={{kind: 'open_evidence', citation_id: id}} context={context} sourceTitles={sourceTitles} onAction={onAction} />)}</div>;
}
