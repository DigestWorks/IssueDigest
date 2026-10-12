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
export function Basis({value}: {value: Claim['basis']}) {
  return <span className="id-canvas-basis">{bases[value]}</span>;
}
export function speaker(claim: Claim, context: DisplayContext) {
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
function actionLabel(action: CanvasAction, context: DisplayContext) {
  switch (action.kind) {
    case 'open_evidence': {
      const display = context.citations.get(action.citation_id)!;
      return `근거 열기: ${display.proof.document.source_id} · ${location(display)}`;
    }
    case 'select_document': return `문서 선택: ${context.documents.get(action.document_id)!.source_id}`;
    case 'ask_question': return `후속 질문: ${action.question}`;
    case 'sort': return `정렬: ${action.field === 'title' ? '제목' : '자료 날짜'} · ${action.direction === 'asc' ? '오름차순' : '내림차순'}`;
  }
}
export function ActionButton({action, context, onAction}: {
  action: CanvasAction; context: DisplayContext; onAction: ActionHandler;
}) {
  return <button type="button" disabled={!onAction} onClick={() => onAction?.(action)}>{actionLabel(action, context)}</button>;
}
export function EvidenceCard({display, context, onAction}: {
  display: CitationDisplay; context: DisplayContext; onAction: ActionHandler;
}) {
  return <figure className="id-canvas-evidence">
    <figcaption><strong>문서 · {display.proof.document.source_id}</strong><span>{display.proof.document.provider}</span><span>{location(display)}</span></figcaption>
    <blockquote>{display.citation.selector.quote}</blockquote>
    <ActionButton action={{kind: 'open_evidence', citation_id: display.citation.citation_id}} context={context} onAction={onAction} />
  </figure>;
}
export function EvidenceLinks({ids, context, onAction}: {
  ids: string[]; context: DisplayContext; onAction: ActionHandler;
}) {
  return <div className="id-canvas-evidence-links">{ids.map(id => <ActionButton key={id} action={{kind: 'open_evidence', citation_id: id}} context={context} onAction={onAction} />)}</div>;
}
