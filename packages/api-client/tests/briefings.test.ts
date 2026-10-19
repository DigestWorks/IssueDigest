import {afterEach, expect, test, vi} from 'vitest';
import * as api from '../src/index';
import fixture from '../../../tests/fixtures/public-briefing-v1.json';
const headers = {'Content-Type':'application/json','Cache-Control':'no-store','X-Request-ID':'00000000-0000-4000-8000-000000000001'};
const response = (value:unknown, status=200, custom:Record<string,string>=headers) => new Response(JSON.stringify(value),{status,headers:custom});
afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});
const summary = () => ({slug:fixture.slug,public_id:fixture.public_id,version:fixture.version,title:fixture.title,description:fixture.description,as_of:fixture.as_of,published_at:fixture.published_at,content_sha256:fixture.content_sha256});
test('reads actual public summaries and a fixed-version exact Canvas anonymously with no-store',async()=>{
 const fetch=vi.fn(async(path:string)=>response(path.endsWith('/briefings')?{items:[summary()]}:fixture));vi.stubGlobal('fetch',fetch);
 expect((await api.listPublicBriefings()).data.items[0]).toEqual(summary());
 expect((await api.getPublicBriefing(fixture.slug,1)).data).toEqual(fixture);
 expect(fetch.mock.calls[1]?.[0]).toBe('/api/v1/briefings/synthetic-policy/versions/1');
 expect(fetch).toHaveBeenCalledWith(expect.any(String),expect.objectContaining({method:'GET',cache:'no-store'}));
});
test.each([
 ['unknown field',(v:typeof fixture)=>{Object.assign(v,{reviewer:'private'});}],
 ['bad slug',(v:typeof fixture)=>{v.slug='other-policy';}],
 ['wrong version',(v:typeof fixture)=>{v.version=2;}],
 ['bad UTC',(v:typeof fixture)=>{v.as_of='2026-02-30T00:00:00Z';}],
 ['hash',(v:typeof fixture)=>{v.content_sha256='no';}],
 ['source crossref',(v:typeof fixture)=>{v.sources[0].document_id=v.public_id;}],
 ['source title',(v:typeof fixture)=>{Object.assign(v.source_titles,{[v.sources[0].document_id]:'mismatch'});}],
 ['private provenance',(v:typeof fixture)=>{v.canvas.research.evidence[0].document.provider='private';}],
 ['source hash',(v:typeof fixture)=>{v.sources[0].text_sha256='b'.repeat(64);}],
 ['exact quote',(v:typeof fixture)=>{v.canvas.research.evidence[0].citations[0].selector.quote='wrong';}],
 ['bad module crossref',(v:typeof fixture)=>{v.canvas.revision.draft.modules[0].claim_ids=[v.public_id];}],
 ['unknown selector field',(v:typeof fixture)=>{Object.assign(v.canvas.research.evidence[0].citations[0].selector,{reviewer:'private'});}],
 ['unknown table field',(v:typeof fixture)=>{Object.assign(v.canvas.research.evidence[0].representation.tables[0],{private_id:v.public_id});}],
 ['private extra evidence',(v:typeof fixture)=>{Object.assign(v.canvas.research.evidence[0],{question:'private'});}],
 ['source date',(v:typeof fixture)=>{v.sources[0].published_on='2026-10-17';}],
 ['unsafe official URL',(v:typeof fixture)=>{v.sources[0].official_url+='&other=1';}],
] as const)('rejects malformed public %s',async(_label, mutate)=>{
 const value=structuredClone(fixture);mutate(value);vi.stubGlobal('fetch',async()=>response(value));
 await expect(api.getPublicBriefing(fixture.slug,1)).rejects.toMatchObject({kind:'malformed'});
});
test.each(['0','01','1.0','+1','9007199254740992','1e2'])('rejects invalid version %s before HTTP',async version=>{
 const fetch=vi.fn();vi.stubGlobal('fetch',fetch);
 await expect(Promise.resolve().then(()=>api.getPublicBriefing(fixture.slug,version))).rejects.toMatchObject({kind:'malformed'});expect(fetch).not.toHaveBeenCalled();
});
test.each([{}, {items:[summary(),summary()]}, {items:Array.from({length:21},()=>summary())}])('rejects malformed list',async value=>{
 vi.stubGlobal('fetch',async()=>response(value));await expect(api.listPublicBriefings()).rejects.toMatchObject({kind:'malformed'});
});
test.each([404,503,401])('keeps public HTTP %s distinct',async status=>{
 vi.stubGlobal('fetch',async()=>response({},status));await expect(api.getPublicBriefing(fixture.slug)).rejects.toMatchObject({kind:status===404?'not-found':status===401?'unauthorized':'unavailable'});
});
test('rejects missing cache boundary and distinguishes interruption from offline',async()=>{
 vi.stubGlobal('fetch',async()=>response(fixture,200,{'Content-Type':'application/json','X-Request-ID':headers['X-Request-ID']}));
 await expect(api.getPublicBriefing(fixture.slug)).rejects.toMatchObject({kind:'malformed'});
 vi.stubGlobal('fetch',async()=>{throw Error('offline');});await expect(api.getPublicBriefing(fixture.slug)).rejects.toMatchObject({kind:'network'});
 const abort=new AbortController();abort.abort();await expect(api.getPublicBriefing(fixture.slug,1,{signal:abort.signal})).rejects.toMatchObject({kind:'aborted'});
 vi.useFakeTimers();vi.stubGlobal('fetch',()=>new Promise(()=>{}));const pending=expect(api.getPublicBriefing(fixture.slug,1,{timeoutMs:5})).rejects.toMatchObject({kind:'timeout'});await vi.advanceTimersByTimeAsync(6);await pending;
});

test.each(['v3', 'v4', 'v5'].flatMap(version => [false, true].map(stripped => ({version, stripped}))))('public profile rejects private $version when stripped=$stripped',async ({version, stripped})=>{
 const value=structuredClone(fixture) as unknown as api.PublicBriefingDetail;
 const claim=value.canvas.research.claims[0]!;
 claim.derivation!.method_version=`research-${version}`;
 if(!stripped) value.canvas.research.support_reviews=[{
  review_id:'00000000-0000-4000-8000-000000000999', reviewer_kind:'automated',
  reviewer_id:`issuedigest-research-${version}`, method:'pydantic-ai', method_version:`research-${version}`,
  reviewed_at:value.canvas.revision.validated_at, rationale:'합성 설명', citation_ids:claim.citation_ids,
  target:{kind:'claim',claim_id:claim.claim_id},scope:'content',assessment:'supported',
 }];
 vi.stubGlobal('fetch',async()=>response(value));
 await expect(api.getPublicBriefing(fixture.slug,1)).rejects.toMatchObject({kind:'malformed'});
});
