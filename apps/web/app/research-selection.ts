import type {ResearchSourceCatalog} from '@issuedigest/api-client';
const normalize = (value: string) => value.normalize('NFKC').toLocaleLowerCase('ko-KR');
const generic = /^(정리|설명|알려|근거|비교|내용|주세요|해줘|해주|주세|무엇|어떻게|대한|관련|요약|핵심|부탁|대해|알고|싶어|있는|해주세요)/;
function words(value: string) {
  return [...new Set((normalize(value).match(/[\p{L}\p{N}]+/gu) ?? []).filter(word => word.length >= 2 && !generic.test(word)))];
}
/** Conservative catalog candidate matching; this does not perform retrieval or web search. */
export function suggestResearchSources(question: string, sources: ResearchSourceCatalog['items']): string[] {
  const tokens = words(question);
  return sources.map((source, index) => {
    const title = words(source.title), excerpt = words(source.excerpt ?? '');
    const bill = source.bill_number ? normalize(source.bill_number) : null;
    const exactBill = bill && tokens.includes(bill) ? 1 : 0;
    const titleMatches = tokens.filter(token => title.includes(token)).length;
    const excerptMatches = tokens.filter(token => excerpt.includes(token)).length;
    return {id:source.snapshot_id, index, exactBill, titleMatches, excerptMatches};
  }).filter(item => item.exactBill || item.titleMatches || item.excerptMatches)
    .sort((a,b) => b.exactBill-a.exactBill || b.titleMatches-a.titleMatches || b.excerptMatches-a.excerptMatches || a.index-b.index)
    .slice(0,3).map(item => item.id);
}
