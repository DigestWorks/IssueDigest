import {expect, it} from 'vitest';
import {suggestResearchSources} from '../app/research-selection';
import type {ResearchSourceCatalog} from '@issuedigest/api-client';
const items = [
  {snapshot_id:'a', title:'기록 관리법', bill_number:'2201234', excerpt:'공공 교통 확대'},
  {snapshot_id:'b', title:'청년 교통 지원법', bill_number:'2201235', excerpt:'지원 내용'},
  {snapshot_id:'c', title:'교통 운영법', bill_number:null, excerpt:'청년 지원'},
  {snapshot_id:'d', title:'교통 검토법', bill_number:null, excerpt:''},
] as ResearchSourceCatalog['items'];
it('prioritizes exact normalized bill numbers and title words, with stable catalog ties and a maximum of three', () => {
  expect(suggestResearchSources('２２０１２３４ 교통 정리해 주세요', items)).toEqual(['a','b','c']);
  expect(suggestResearchSources('교통', items)).toEqual(['b','c','d']);
});
it('does not turn generic requests or unrelated questions into arbitrary first sources', () => {
  for (const question of ['정리 설명 알려 근거 비교 내용 주세요', '우주 탐사 현황', 'a 및']) expect(suggestResearchSources(question, items)).toEqual([]);
});
it('normalizes English case and full-width characters', () => {
  expect(suggestResearchSources('ＡＩ POLICY', [{...items[0], title:'AI policy 법안'}])).toEqual(['a']);
});
