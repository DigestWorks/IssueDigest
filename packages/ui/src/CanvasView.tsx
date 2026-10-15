import type { CanvasAction, CanvasBundle } from '@issuedigest/api-client';
import { prepareCanvas } from './prepare';
import { ModuleContent } from './modules';
import { ActionButton } from './components';

export type CanvasViewProps = {
  bundle: CanvasBundle | null;
  sourceTitles?: Record<string, string>;
  onAction?: (action: CanvasAction) => void;
};

export function CanvasView({bundle, onAction, sourceTitles}: CanvasViewProps) {
  if (bundle === null) return <div className="id-canvas"><p role="status" className="id-canvas-state">아직 표시할 조사 자료가 없습니다.</p></div>;
  const prepared = prepareCanvas(bundle);
  if (prepared.status === 'rejected') return <div className="id-canvas"><p role="alert" className="id-canvas-state">이 화면을 안전하게 표시할 수 없습니다. 검증된 최신 자료를 다시 확인해 주세요.</p></div>;
  return <article className="id-canvas" aria-label="조사 화면">
    <header className="id-canvas-header"><h2>조사 결과</h2></header>
    {prepared.status === 'message' ? <div role="status" className="id-canvas-state"><h3>{prepared.outcome === 'insufficient_evidence' ? '근거가 부족합니다' : '추가 질문이 필요합니다'}</h3><p>{prepared.message}</p></div> : <div className="id-canvas-grid">{prepared.modules.map(module => <section key={module.module_id} aria-label={module.title} data-span={module.span} className="id-canvas-module">
      <h3>{module.title}</h3>
      <ModuleContent module={module} context={prepared.context} sourceTitles={sourceTitles} onAction={onAction} />
      {module.actions.length > 0 && (!sourceTitles || module.actions.some(action => action.kind !== 'open_evidence')) && <footer className="id-canvas-actions" aria-label={`${module.title} 액션`}>{module.actions.map((action, index) => <ActionButton key={index} action={action} context={prepared.context} sourceTitles={sourceTitles} onAction={onAction} />)}</footer>}
    </section>)}</div>}
  </article>;
}
