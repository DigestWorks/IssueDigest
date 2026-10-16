import type { CanvasModule } from '@issuedigest/api-client';
import { Basis, EvidenceCard, EvidenceLinks, endpointText, predicates, speaker } from './components';
import type { ActionHandler } from './components';
import type { DisplayContext } from './prepare';
import { Chart } from './chart';

export function ModuleContent({module, context, sourceTitles, onAction, presentation = 'canvas'}: {
  presentation?: 'canvas' | 'briefing'; module: CanvasModule; context: DisplayContext; sourceTitles?: Record<string, string>; onAction: ActionHandler;
}) {
  switch (module.kind) {
    case 'evidence': return <div>{module.citation_ids.map(id => <EvidenceCard key={id} display={context.citations.get(id)!} context={context} sourceTitles={sourceTitles} onAction={onAction} />)}</div>;
    case 'summary': return <ul className="id-canvas-claims">{module.claim_ids.map(id => {
      const claim = context.claims.get(id)!;
      return <li key={id}><p className="id-canvas-attribution">{speaker(claim, context, sourceTitles)} <Basis value={claim.basis} aiGenerated={Boolean(sourceTitles)} /></p><p>{claim.text}</p><EvidenceLinks ids={claim.citation_ids} context={context} sourceTitles={sourceTitles} onAction={onAction} /></li>;
    })}</ul>;
    case 'comparison': if (presentation === 'briefing') return <>
      <p className="id-canvas-note">{sourceTitles ? '자료별 AI 해석을 주장별로 읽습니다.' : '전달된 주장을 하나씩 읽습니다.'}</p>
      <ol className="id-canvas-claims" aria-label="주장별 비교">{module.claim_ids.map(id => {
        const claim = context.claims.get(id)!;
        return <li key={id}><p className="id-canvas-attribution">{speaker(claim, context, sourceTitles)} <Basis value={claim.basis} aiGenerated={Boolean(sourceTitles)} /></p><p>{claim.text}</p><EvidenceLinks ids={claim.citation_ids} context={context} sourceTitles={sourceTitles} onAction={onAction} /></li>;
      })}</ol>
    </>;
    return <>
      <p className="id-canvas-note">{sourceTitles ? '자료별 AI 해석을 나란히 봅니다.' : '전달된 주장을 나란히 표시합니다. 수치 합산이나 주장 간 동등성을 평가하지 않았습니다.'}</p>
      <div className="id-canvas-table-scroll" tabIndex={0} role="group" aria-label="주장 비교 표 가로 스크롤">
        <table><caption>주장 비교</caption><thead><tr><th scope="col">{sourceTitles ? '근거 자료' : '발화 주체'}</th><th scope="col">내용</th><th scope="col">구분</th><th scope="col">근거</th></tr></thead>
          <tbody>{module.claim_ids.map(id => {
            const claim = context.claims.get(id)!;
            return <tr key={id}><th scope="row">{speaker(claim, context, sourceTitles)}</th><td>{claim.text}</td><td><Basis value={claim.basis} aiGenerated={Boolean(sourceTitles)} /></td><td><EvidenceLinks ids={claim.citation_ids} context={context} sourceTitles={sourceTitles} onAction={onAction} /></td></tr>;
          })}</tbody>
        </table>
      </div>
    </>;
    case 'timeline': {
      const claims = module.claim_ids.map(id => context.claims.get(id)!).sort((a, b) => a.valid_period!.start_date.localeCompare(b.valid_period!.start_date) || a.valid_period!.end_date.localeCompare(b.valid_period!.end_date));
      return <ol className="id-canvas-timeline">{claims.map(claim => <li key={claim.claim_id}>
        <p className="id-canvas-period">{claim.valid_period!.start_date === claim.valid_period!.end_date ? claim.valid_period!.start_date : `${claim.valid_period!.start_date} – ${claim.valid_period!.end_date}`}</p>
        <p className="id-canvas-attribution">{speaker(claim, context, sourceTitles)} <Basis value={claim.basis} aiGenerated={Boolean(sourceTitles)} /></p><p>{claim.text}</p>
        <EvidenceLinks ids={claim.citation_ids} context={context} sourceTitles={sourceTitles} onAction={onAction} />
      </li>)}</ol>;
    }
    case 'graph': return <div className="id-canvas-relations">{module.relation_ids.map(id => {
      const relation = context.relations.get(id)!;
      const source = endpointText(relation.source, context), target = endpointText(relation.target, context);
      const predicate = predicates[relation.predicate];
      return <figure key={id}>
        <div className="id-canvas-connection" role="img" aria-label={`${source} → ${predicate} → ${target}`}>
          <span className="id-canvas-node">{source}</span><span className="id-canvas-edge"><span>{predicate}</span><span aria-hidden="true">⟶</span></span><span className="id-canvas-node">{target}</span>
        </div>
        <figcaption><Basis value={relation.basis} /></figcaption>
        <EvidenceLinks ids={relation.citation_ids} context={context} sourceTitles={sourceTitles} onAction={onAction} />
      </figure>;
    })}</div>;
    case 'chart': return <Chart module={module} context={context} onAction={onAction} />;
  }
}
