import type { CanvasAction, CanvasBundle } from '@issuedigest/api-client';
import { prepareCanvas } from './prepare';
import { ModuleContent } from './modules';
import { ActionButton } from './components';

export type CanvasViewProps = {
  bundle: CanvasBundle | null;
  presentation?: 'canvas' | 'briefing';
  sourceTitles?: Record<string, string>;
  onAction?: (action: CanvasAction) => void;
};

export function CanvasView({bundle, onAction, sourceTitles, presentation = 'canvas'}: CanvasViewProps) {
  if (bundle === null) return <div className="id-canvas"><p role="status" className="id-canvas-state">아직 표시할 조사 자료가 없습니다.</p></div>;
  const prepared = prepareCanvas(bundle);
  if (prepared.status === 'rejected') return <div className="id-canvas"><p role="alert" className="id-canvas-state">이 화면을 안전하게 표시할 수 없습니다. 검증된 최신 자료를 다시 확인해 주세요.</p></div>;
  const briefing = presentation === 'briefing';
  const modules = prepared.status === 'ready' ? prepared.modules : [];
  const lead = modules.find(module => module.kind === 'summary') ?? modules[0];
  const ordered = briefing && lead ? [lead, ...modules.filter(module => module !== lead)] : modules;
  return <article className="id-canvas" data-presentation={presentation} aria-label="브리핑 화면">
    <header className="id-canvas-header"><h2>브리핑</h2></header>
    {prepared.status === 'message' ? <div role="status" className="id-canvas-state"><h3>{prepared.outcome === 'insufficient_evidence' ? '근거가 부족합니다' : '추가 질문이 필요합니다'}</h3><p>{prepared.message}</p></div> : <div className="id-canvas-grid">{ordered.map((module, index) => {
      const content = <section key={module.module_id} aria-label={module.title} data-span={module.span} className="id-canvas-module">
      {(!briefing || index === 0) && <h3>{module.title}</h3>}
      <ModuleContent presentation={presentation} module={module} context={prepared.context} sourceTitles={sourceTitles} onAction={onAction} />
      {module.actions.length > 0 && (!sourceTitles || module.actions.some(action => action.kind !== 'open_evidence')) && <footer className="id-canvas-actions" aria-label={`${module.title} 액션`}>{module.actions.map((action, index) => <ActionButton key={index} action={action} context={prepared.context} sourceTitles={sourceTitles} onAction={onAction} />)}</footer>}
    </section>;
      return briefing && index > 0 ? <details className="id-briefing-detail" key={module.module_id}><summary>{module.title}</summary>{content}</details> : content;
    })}</div>}
  </article>;
}
