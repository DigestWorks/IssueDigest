import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { CanvasAction, CanvasBundle } from '@issuedigest/api-client';
import fixture from '../../../tests/fixtures/canvas-synthetic.json';
import { CanvasView } from '../src';

// Python validates this shared fixture; the assertion gives the React consumer the generated type.
const typedFixture: CanvasBundle = fixture as CanvasBundle;
function data(): CanvasBundle { return structuredClone(typedFixture); }
const unknown = '00000000-0000-4000-8000-999999999999';

describe('CanvasView', () => {
  it('uses verified source titles for AI inference and citation actions without exposing source IDs', () => {
    const bundle = data();
    bundle.research.claims[0].speaker_entity_id = null;
    bundle.research.claims[0].basis = 'inference';
    render(<CanvasView bundle={bundle} sourceTitles={{[bundle.research.evidence[0].document.document_id]: '실제 법안 제목'}} />);
    expect(screen.getAllByText('실제 법안 제목').length).toBeGreaterThan(0);
    expect(screen.getAllByText('AI 해석').length).toBeGreaterThan(0);
    expect(screen.queryByText(/발화 주체 미제공/)).not.toBeInTheDocument();
    expect(screen.queryByText(/화면 버전/)).not.toBeInTheDocument();
  });
  it('shows a short named-source citation button while preserving its full accessible label and action', async () => {
    const bundle = data();
    const received: CanvasAction[] = [];
    const title = '실제 법안 제목';
    render(<CanvasView bundle={bundle} sourceTitles={{[bundle.research.evidence[0].document.document_id]: title}} onAction={action => received.push(action)} />);
    const button = screen.getAllByRole('button', {name: /^근거 열기: 실제 법안 제목 ·/})[0];
    expect(button).toHaveTextContent(/^근거 열기$/);
    expect(button).toHaveAttribute('title', expect.stringContaining(title));
    await userEvent.setup().click(button);
    expect(received).toEqual([{kind: 'open_evidence', citation_id: bundle.research.evidence[0].citations[0].citation_id}]);
  });
  it('shows an empty state instead of fabricating modules', () => {
    render(<CanvasView bundle={null} />);
    expect(screen.getByRole('status')).toHaveTextContent('아직 표시할 조사 자료가 없습니다');
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
  });

  it('renders all six modules in supplied order and span with selected evidence only', () => {
    render(<CanvasView bundle={data()} />);
    expect(screen.getByRole('heading', {name: '조사 결과'})).toBeInTheDocument();
    expect(screen.getAllByRole('region').map(section => section.getAttribute('aria-label')))
      .toEqual(['합성 근거', '합성 요약', '합성 비교', '합성 타임라인', '합성 관계', '합성 수치']);
    expect(screen.getByRole('region', {name: '합성 비교'})).toHaveAttribute('data-span', 'full');
    const evidence = screen.getByRole('region', {name: '합성 근거'});
    expect(within(evidence).getAllByText('합성 문서 A')).toHaveLength(3);
    expect(within(evidence).getByText('페이지 1 · 문자 0–38')).toBeInTheDocument();
    expect(within(evidence).getByText('텍스트 · 문자 0–38')).toBeInTheDocument();
    expect(within(evidence).getByText('표 synthetic-table · 셀 synthetic-cell')).toBeInTheDocument();
    expect(within(evidence).getByText('합성 표 인용')).toBeInTheDocument();
    expect(screen.queryByText(/선택하지 않은 합성 문서 B/)).not.toBeInTheDocument();
  });

  it('changes composition exactly with modules and never modifies frozen input', () => {
    const bundle = data();
    bundle.revision.draft.modules = [bundle.revision.draft.modules[5], bundle.revision.draft.modules[0]];
    bundle.revision.draft.modules[0].span = 'half';
    const before = JSON.stringify(bundle);
    function freeze(value: object) {
      Object.freeze(value);
      Object.values(value).forEach(item => { if (item && typeof item === 'object') freeze(item); });
    }
    freeze(bundle);
    render(<CanvasView bundle={bundle} />);
    expect(screen.getAllByRole('region').map(section => section.getAttribute('aria-label'))).toEqual(['합성 수치', '합성 근거']);
    expect(screen.getByRole('region', {name: '합성 수치'})).toHaveAttribute('data-span', 'half');
    expect(JSON.stringify(bundle)).toBe(before);
  });

  it('allows consistent shared document metadata across versions regardless of property order', () => {
    const bundle=data();
    const original=bundle.research.evidence[0].document;
    bundle.research.evidence[1].document={
      provider:original.provider, source_id:original.source_id, source_kind:original.source_kind,
      canonical_url:original.canonical_url, workspace_id:original.workspace_id, document_id:original.document_id,
    };
    bundle.research.evidence[1].version.document_id=original.document_id;
    render(<CanvasView bundle={bundle} />);
    expect(screen.getAllByRole('region')).toHaveLength(6);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('preserves attribution and distinguishes all claim bases in summary and comparison', () => {
    render(<CanvasView bundle={data()} />);
    for (const name of ['합성 요약', '합성 비교']) {
      const module = within(screen.getByRole('region', {name}));
      expect(module.getByText('합성 주장: 나중 구간')).toBeInTheDocument();
      expect(module.getByText('합성 관측: 앞선 구간')).toBeInTheDocument();
      expect(module.getByText('합성 추론: 중간 구간')).toBeInTheDocument();
      expect(module.getByText('원문 주장')).toBeInTheDocument();
      expect(module.getByText('관측')).toBeInTheDocument();
      expect(module.getByText('추론')).toBeInTheDocument();
      expect(module.getAllByText('합성 주체 A')).toHaveLength(2);
      expect(module.getByText('합성 주체 B')).toBeInTheDocument();
      expect(module.getAllByRole('button', {name:/근거 열기/}).length).toBeGreaterThanOrEqual(3);
    }
    expect(within(screen.getByRole('region', {name:'합성 비교'})).getByRole('table')).toHaveAccessibleName('주장 비교');
  });

  it('sorts timeline by known date intervals without collapsing them to event instants', () => {
    render(<CanvasView bundle={data()} />);
    const timeline = within(screen.getByRole('region', {name:'합성 타임라인'}));
    expect(timeline.getAllByRole('listitem').map(item => within(item).getByText(/합성 (주장|관측|추론):/).textContent))
      .toEqual(['합성 관측: 앞선 구간', '합성 추론: 중간 구간', '합성 주장: 나중 구간']);
    expect(timeline.getByText('2026-01-01 – 2026-01-31')).toBeInTheDocument();
    expect(timeline.getByText('2026-03-01 – 2026-03-31')).toBeInTheDocument();
  });

  it('shows the actual directed relation and basis as connected nodes and readable text', () => {
    render(<CanvasView bundle={data()} />);
    const graph = within(screen.getByRole('region', {name:'합성 관계'}));
    expect(graph.getByRole('img', {name:'합성 주장: 나중 구간 → 지지 → 합성 관측: 앞선 구간'})).toBeInTheDocument();
    expect(graph.getByText('원문 주장')).toBeInTheDocument();
    expect(graph.getByText('지지')).toBeInTheDocument();
    expect(graph.getAllByRole('button', {name:/근거 열기/}).length).toBeGreaterThan(0);
  });

  it('renders real signed bars, exact decimals, comparable conditions and a numeric table', () => {
    const {container} = render(<CanvasView bundle={data()} />);
    const chart = within(screen.getByRole('region', {name:'합성 수치'}));
    expect(chart.getByRole('table', {name:'수치와 근거'})).toBeInTheDocument();
    expect(chart.getAllByText('-25.000000000000000001')).toHaveLength(2);
    expect(chart.getAllByText('50.000000000000000002')).toHaveLength(2);
    expect(chart.getByText('합성 모집단')).toBeInTheDocument();
    expect(chart.getAllByText('합성 단위')).toHaveLength(4);
    expect(chart.getByText('2026-01-01 – 2026-01-31')).toBeInTheDocument();
    const bars = container.querySelectorAll('rect[data-observation-id]');
    expect(bars).toHaveLength(3);
    expect(Number(bars[0].getAttribute('width'))).toBeCloseTo(100, 3);
    expect(Number(bars[1].getAttribute('width'))).toBe(0);
    expect(Number(bars[2].getAttribute('width'))).toBeCloseTo(200, 3);
    expect(Number(bars[0].getAttribute('x'))).toBe(0);
    expect(Number(bars[2].getAttribute('x'))).toBeCloseTo(100, 3);
  });

  it.each([
    ['introduced_by','발의자','합성 주체 A','합성 주체 B'],
    ['reviewed_by','심사 주체','합성 주체 A','합성 주체 B'],
    ['alternative_to','대안 관계','합성 주체 A','합성 주체 B'],
    ['supports','지지','합성 주장: 나중 구간','합성 관측: 앞선 구간'],
    ['contradicts','상충','합성 주장: 나중 구간','합성 관측: 앞선 구간'],
    ['mentions','언급','합성 문서 A','합성 주체 B'],
  ] as const)('shows %s in readable Korean while resolving the supplied typed endpoints', (predicate, meaning, source, target) => {
    const bundle=data();
    bundle.revision.draft.modules=[bundle.revision.draft.modules[4]];
    const relation=bundle.research.relations[0];
    relation.predicate=predicate;
    if (predicate === 'mentions') {
      relation.source={kind:'document',document_id:bundle.research.evidence[0].document.document_id};
      relation.target={kind:'entity',entity_id:bundle.research.entities[1].entity_id};
    } else if (predicate !== 'supports' && predicate !== 'contradicts') {
      bundle.research.entities[0].kind='bill';
      if(predicate === 'alternative_to') bundle.research.entities[1].kind='bill';
      relation.source={kind:'entity',entity_id:bundle.research.entities[0].entity_id};
      relation.target={kind:'entity',entity_id:bundle.research.entities[1].entity_id};
    }
    render(<CanvasView bundle={bundle} />);
    expect(screen.getByRole('img',{name:`${source} → ${meaning} → ${target}`})).toBeInTheDocument();
    expect(screen.getByText(meaning)).toBeInTheDocument();
  });

  it('compares supplied periods and dimensions by meaning rather than JSON property order', () => {
    const bundle=data();
    for (const observation of bundle.research.observations) {
      observation.context.dimensions=[{key:'합성 분류',value:'A'},{key:'합성 조건',value:'B'}];
    }
    bundle.research.observations[1].context.period={end_date:'2026-01-31',start_date:'2026-01-01'};
    bundle.research.observations[1].context.dimensions=[{value:'B',key:'합성 조건'},{value:'A',key:'합성 분류'}];
    render(<CanvasView bundle={bundle} />);
    expect(screen.getByRole('table',{name:'수치와 근거'})).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it.each([
    ['0','0','0'], ['5','5','5'], ['-5','-10','0'],
    ['99999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999','1','0'],
    ['0.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001','0','-0.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001'],
  ])('keeps finite proportional geometry and exact labels for decimal extremes %j', (...values) => {
    const bundle=data();
    bundle.research.observations.forEach((observation,index) => { observation.value=values[index]; observation.raw_value=values[index]; });
    const {container}=render(<CanvasView bundle={bundle} />);
    const bars=[...container.querySelectorAll('rect[data-observation-id]')];
    expect(bars).toHaveLength(3);
    bars.forEach((bar,index) => {
      const width=Number(bar.getAttribute('width'));
      expect(Number.isFinite(width)).toBe(true);
      expect(width).toBeGreaterThanOrEqual(0);
      expect(width).toBeLessThanOrEqual(300);
      expect(screen.getAllByText(values[index]).length).toBeGreaterThan(0);
    });
    if (values[0] === '5') expect(bars.map(bar=>Number(bar.getAttribute('width')))).toEqual([300,300,300]);
    if (values[0] === '-5') expect(bars.map(bar=>Number(bar.getAttribute('width')))).toEqual([150,300,0]);
  });

  it.each(['insufficient_evidence', 'clarification_needed'] as const)('shows %s with the supplied message and no modules', outcome => {
    const bundle=data();
    bundle.revision.draft={...bundle.revision.draft,outcome,modules:[],message:'합성 안내: 추가 자료 필요'};
    render(<CanvasView bundle={bundle} />);
    expect(screen.getByRole('status')).toHaveTextContent('합성 안내: 추가 자료 필요');
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
  });

  it('renders hostile text as plain text and never exposes executable markup or external links', () => {
    const bundle=data();
    bundle.research.claims[0].text='<img src=x onerror="alert(1)"><script>bad()</script> https://evil.invalid';
    bundle.revision.draft.modules[0].title='<svg onload="bad()">';
    bundle.research.evidence[0].document.canonical_url='https://evil.invalid';
    const {container}=render(<CanvasView bundle={bundle} />);
    expect(screen.getAllByText(bundle.research.claims[0].text).length).toBeGreaterThan(0);
    expect(container.querySelector('script, img, a, iframe')).toBeNull();
  });

  it('passes allowed actions on keyboard input only, with no automatic callback', async () => {
    const received: CanvasAction[]=[];
    const bundle=data();
    render(<CanvasView bundle={bundle} onAction={action=>received.push(action)} />);
    expect(received).toEqual([]);
    const user=userEvent.setup();
    const evidence=within(screen.getByRole('region',{name:'합성 근거'}));
    const buttons=[evidence.getByRole('button',{name:'문서 선택: 합성 문서 A'}),evidence.getByRole('button',{name:'후속 질문: 합성 후속 질문?'}),evidence.getByRole('button',{name:'정렬: 제목 · 오름차순'}),evidence.getByRole('button',{name:'정렬: 자료 날짜 · 내림차순'})];
    for (const button of buttons) {button.focus();await user.keyboard('{Enter}');}
    expect(received).toEqual(bundle.revision.draft.modules[0].actions.slice(1));
    const citationButton=evidence.getAllByRole('button',{name:/근거 열기/})[0];
    citationButton.focus();await user.keyboard(' ');
    expect(received.at(-1)).toEqual({kind:'open_evidence',citation_id:bundle.research.evidence[0].citations[0].citation_id});
  });

  it('disables every evidence and module action without a host callback', () => {
    render(<CanvasView bundle={data()} />);
    const buttons=screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(6);
    buttons.forEach(button=>expect(button).toBeDisabled());
  });
});

// A broken reference anywhere must reject the whole screen, including earlier valid modules.
const invalidCases: [string,(bundle: CanvasBundle)=>void][]=[
  ['workspace',b=>{b.revision.workspace_id=unknown;}],
  ['record workspace',b=>{b.research.entities[0].workspace_id=unknown;}],
  ['research version',b=>{Object.assign(b.research,{schema_version:2});}],
  ['revision version',b=>{Object.assign(b.revision,{schema_version:2});}],
  ['draft version',b=>{Object.assign(b.revision.draft,{schema_version:2});}],
  ['policy',b=>{Object.assign(b.revision,{validation_policy:'future'});}],
  ['evidence version',b=>{Object.assign(b.research.evidence[0],{schema_version:2});}],
  ['failed outcome',b=>{b.revision.draft.outcome='provider_refusal';}],
  ['incomplete outcome',b=>{b.revision.draft.outcome='incomplete_output';}],
  ['unknown outcome',b=>{Object.assign(b.revision.draft,{outcome:'unknown'});}],
  ['empty answer',b=>{b.revision.draft.modules=[];}],
  ['nonanswer modules',b=>{b.revision.draft.outcome='clarification_needed';b.revision.draft.message='raw secret';}],
  ['unknown module',b=>{Object.assign(b.revision.draft.modules[5],{kind:'html'});}],
  ['unknown span',b=>{Object.assign(b.revision.draft.modules[5],{span:'third'});}],
  ['unknown action',b=>{Object.assign(b.revision.draft.modules[5].actions[0],{kind:'execute',url:'https://evil.invalid'});}],
  ['invalid sort',b=>{Object.assign(b.revision.draft.modules[0].actions[3],{field:'script'});}],
  ['invalid direction',b=>{Object.assign(b.revision.draft.modules[0].actions[3],{direction:'random'});}],
  ['empty question',b=>{Object.assign(b.revision.draft.modules[0].actions[2],{question:' '});}],
  ['unknown selected version',b=>{b.revision.selected_version_ids=[unknown];}],
  ['unselected citation',b=>{b.revision.draft.modules[0].citation_ids=[b.research.evidence[1].citations[0].citation_id];}],
  ['duplicate module',b=>{b.revision.draft.modules.push(structuredClone(b.revision.draft.modules[0]));}],
  ['duplicate citation',b=>{b.research.evidence[0].citations.push(structuredClone(b.research.evidence[0].citations[0]));}],
  ['duplicate claim',b=>{b.research.claims.push(structuredClone(b.research.claims[0]));}],
  ['duplicate entity',b=>{b.research.entities.push(structuredClone(b.research.entities[0]));}],
  ['duplicate relation',b=>{b.research.relations.push(structuredClone(b.research.relations[0]));}],
  ['duplicate observation',b=>{b.research.observations.push(structuredClone(b.research.observations[0]));}],
  ['citation version chain',b=>{b.research.evidence[0].citations[0].document_version_id=unknown;}],
  ['citation representation chain',b=>{b.research.evidence[0].citations[0].representation_id=unknown;}],
  ['conflicting document',b=>{b.research.evidence[1].document.document_id=b.research.evidence[0].document.document_id;b.research.evidence[1].version.document_id=b.research.evidence[0].document.document_id;}],
  ['missing claim',b=>{b.research.claims=[];}],
  ['wrong entity reference',b=>{b.research.claims[0].speaker_entity_id=b.research.claims[0].claim_id;}],
  ['missing relation',b=>{b.research.relations=[];}],
  ['wrong endpoint',b=>{b.research.relations[0].source={kind:'entity',entity_id:b.research.claims[0].claim_id};}],
  ['unknown predicate',b=>{Object.assign(b.research.relations[0],{predicate:'causes'});}],
  ['unknown relation version',b=>{Object.assign(b.research.relations[0],{ontology_version:'future'});}],
  ['missing observation',b=>{b.research.observations=[];}],
  ['union mismatch',b=>{b.revision.draft.modules[1].citation_ids.pop();}],
  ['foreign action citation',b=>{Object.assign(b.revision.draft.modules[5].actions[0],{citation_id:b.research.evidence[0].citations[1].citation_id});}],
  ['unselected action document',b=>{Object.assign(b.revision.draft.modules[0].actions[1],{document_id:b.research.evidence[1].document.document_id});}],
  ['missing valid period',b=>{b.research.claims[0].valid_period=null;}],
  ['unknown claim basis',b=>{Object.assign(b.research.claims[0],{basis:'verified'});}],
  ['unknown chart type',b=>{Object.assign(b.revision.draft.modules[5],{chart_type:'pie'});}],
  ['unknown chart value',b=>{b.research.observations[0].value=null;}],
  ['invalid decimal',b=>{b.research.observations[0].value='Infinity';}],
  ['missing comparison condition',b=>{b.research.observations[0].context.unit=null;}],
  ['different comparison condition',b=>{b.research.observations[0].context.population='다른 합성 모집단';}],
];
it.each(invalidCases)('safely rejects %s without leaking earlier modules or raw reasons', (_name,mutate) => {
  const bundle=data();mutate(bundle);
  render(<CanvasView bundle={bundle} />);
  expect(screen.getByRole('alert')).toHaveTextContent('이 화면을 안전하게 표시할 수 없습니다');
  expect(screen.queryByRole('region')).not.toBeInTheDocument();
  expect(screen.queryByText('raw secret')).not.toBeInTheDocument();
});

it('briefing promotes the supplied summary and folds supporting modules without changing the default table', async () => {
  const bundle = data();
  render(<CanvasView bundle={bundle} presentation="briefing" />);
  const article = screen.getByRole('article');
  expect(article).toHaveAttribute('data-presentation', 'briefing');
  expect(article.querySelector('section')).toHaveAccessibleName('합성 요약');
  const comparison = screen.getByText('합성 비교');
  expect(comparison.closest('details')).not.toHaveAttribute('open');
  await userEvent.setup().click(comparison);
  const region = screen.getByRole('region', {name:'합성 비교'});
  expect(within(region).queryByRole('table')).not.toBeInTheDocument();
  expect(within(region).getByRole('list', {name:'주장별 비교'})).toBeInTheDocument();
  expect(within(region).getByText('합성 주장: 나중 구간')).toBeInTheDocument();
  expect(within(region).getAllByRole('button', {name:/근거 열기/}).length).toBeGreaterThan(0);
});
it.each(['insufficient_evidence', 'clarification_needed'] as const)('briefing keeps the real %s message', outcome => {
  const bundle = data(); bundle.revision.draft={...bundle.revision.draft,outcome,modules:[],message:'서버가 제공한 안내'};
  render(<CanvasView bundle={bundle} presentation="briefing" />);
  expect(screen.getByRole('status')).toHaveTextContent('서버가 제공한 안내');
});
it('briefing rejects broken canonical references and uses the actual first module when summary is absent', () => {
  const bundle = data(); bundle.revision.draft.modules=[bundle.revision.draft.modules[2]];
  const {rerender} = render(<CanvasView bundle={bundle} presentation="briefing" />);
  expect(screen.getByRole('region', {name:'합성 비교'})).toBeInTheDocument();
  bundle.revision.draft.modules[0].citation_ids=['00000000-0000-4000-8000-999999999999'];
  rerender(<CanvasView bundle={bundle} presentation="briefing" />);
  expect(screen.getByRole('alert')).toHaveTextContent('안전하게 표시할 수 없습니다');
});
