import type { ChartModule, Observation } from '@issuedigest/api-client';
import { EvidenceLinks } from './components';
import type { ActionHandler } from './components';
import type { DisplayContext } from './prepare';

/** Use integer arithmetic until the bounded, approximate 300-unit display ratio. */
function geometry(values: string[]) {
  const scale = Math.max(...values.map(value => value.split('.')[1]?.length ?? 0));
  const numbers = values.map(value => {
    const negative = value.startsWith('-');
    const [whole, fraction = ''] = (negative ? value.slice(1) : value).split('.');
    const integer = BigInt(whole + fraction.padEnd(scale, '0'));
    return negative ? -integer : integer;
  });
  const min = numbers.reduce((a, b) => b < a ? b : a, 0n);
  const max = numbers.reduce((a, b) => b > a ? b : a, 0n);
  const range = max - min;
  const ratio = (value: bigint) => range === 0n ? 0 : Number(value * 300_000_000n / range) / 1_000_000;
  const origin = ratio(-min);
  return numbers.map(value => ({x: value < 0n ? ratio(value - min) : origin, width: ratio(value < 0n ? -value : value), origin}));
}
function label(value: Observation, context: DisplayContext) {
  return value.subject_entity_id === null ? '주체 미제공' : context.entities.get(value.subject_entity_id)!.name;
}

export function Chart({module, context, onAction}: {
  module: ChartModule; context: DisplayContext; onAction: ActionHandler;
}) {
  const values = module.observation_ids.map(id => context.observations.get(id)!);
  const bars = geometry(values.map(value => value.value!));
  const conditions = values[0].context;
  return <>
    <dl className="id-canvas-conditions">
      <dt>측정</dt><dd>{conditions.metric}</dd><dt>단위</dt><dd>{conditions.unit}</dd>
      <dt>기간</dt><dd>{conditions.period!.start_date} – {conditions.period!.end_date}</dd>
      <dt>모집단</dt><dd>{conditions.population}</dd><dt>지역</dt><dd>{conditions.geography}</dd>
      <dt>질문</dt><dd>{conditions.question}</dd><dt>방법</dt><dd>{conditions.methodology}</dd>
      <dt>표본 수</dt><dd>{conditions.sample_size}</dd><dt>가중</dt><dd>{conditions.weighting}</dd>
      <dt>분모</dt><dd>{conditions.denominator}</dd><dt>계열</dt><dd>{conditions.series_id}</dd>
      {conditions.dimensions.map(dimension => <div key={dimension.key} className="id-canvas-dimension"><dt>{dimension.key}</dt><dd>{dimension.value}</dd></div>)}
    </dl>
    <p className="id-canvas-note">전달된 비교 조건이 같습니다. 합산 가능성은 평가하지 않았습니다. 막대는 근사 비율이며 정확한 값은 숫자로 표시합니다.</p>
    <div className="id-canvas-bars">{values.map((value, index) => <figure key={value.observation_id}>
      <figcaption><span>{label(value, context)}</span><strong>{value.value}</strong></figcaption>
      <svg viewBox="0 0 300 24" role="img" aria-label={`${label(value, context)}: ${value.value} ${conditions.unit}`}>
        <line x1={bars[index].origin} x2={bars[index].origin} y1="0" y2="24" className="id-canvas-zero" />
        <rect data-observation-id={value.observation_id} x={bars[index].x} y="4" width={bars[index].width} height="16" className={value.value!.startsWith('-') ? 'id-canvas-bar-negative' : 'id-canvas-bar'} />
      </svg>
    </figure>)}</div>
    <div className="id-canvas-table-scroll" tabIndex={0} role="group" aria-label="수치 표 가로 스크롤">
      <table><caption>수치와 근거</caption><thead><tr><th scope="col">주체</th><th scope="col">정확한 값</th><th scope="col">단위</th><th scope="col">근거</th></tr></thead>
        <tbody>{values.map(value => <tr key={value.observation_id}><th scope="row">{label(value, context)}</th><td>{value.value}</td><td>{value.context.unit}</td><td><EvidenceLinks ids={value.citation_ids} context={context} onAction={onAction} /></td></tr>)}</tbody>
      </table>
    </div>
  </>;
}
