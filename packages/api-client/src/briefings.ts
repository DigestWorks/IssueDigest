import type {components} from './schema';
import {hasKeys, isId, isObject, protectedRequest, type ProtectedFailure, type ProtectedOptions} from './protected-request';
import {exactDay, exactTimestamp, validResearchCanvas} from './research-validation';

export type PublicBriefingSummary = components['schemas']['PublicBriefingSummary'];
export type PublicBriefingDetail = components['schemas']['PublicBriefingDetail'];
export type PublicBriefingList = components['schemas']['PublicBriefingList'];
export type PublicSourceAttribution = components['schemas']['PublicSourceAttribution'];
export type PublicBriefingErrorResponse = components['schemas']['PublicBriefingError'];
export type PublicBriefingOptions = ProtectedOptions;
export type PublicBriefingFailure = ProtectedFailure;
export class PublicBriefingError extends Error {
  constructor(public readonly kind: PublicBriefingFailure, public readonly requestId?: string) {
    super(`Public briefing request failed: ${kind}`); this.name = 'PublicBriefingError';
  }
}
const fail = (kind: PublicBriefingFailure, requestId?: string) => new PublicBriefingError(kind, requestId);
const exact = (value: unknown, keys: string[]) => isObject(value) && hasKeys(value,keys);
const summaryKeys = ['slug','public_id','version','title','description','as_of','published_at','content_sha256'];
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.trim().length > 0 && Array.from(value).length <= max;
const hash = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const slug = (value: unknown): value is string => typeof value === 'string' && value.length >= 3 && value.length <= 80 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
const version = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 1;
const official = (value: unknown): value is string => typeof value === 'string' && value.length <= 180 && /^https:\/\/www\.korea\.kr\/news\/policyNewsView\.do\?newsId=[0-9]+$/.test(value);
function validSummary(value: Record<string, unknown>): boolean {
  return slug(value.slug) && isId(value.public_id) && version(value.version) && text(value.title,150)
    && text(value.description,350) && exactTimestamp(value.as_of) && exactTimestamp(value.published_at)
    && Date.parse(value.as_of) <= Date.parse(value.published_at) && hash(value.content_sha256);
}
function validList(value: unknown): value is PublicBriefingList {
  return isObject(value) && hasKeys(value,['items']) && Array.isArray(value.items) && value.items.length <= 20
    && value.items.every(item => isObject(item) && hasKeys(item,summaryKeys) && validSummary(item))
    && new Set(value.items.map(item => item.slug)).size === value.items.length;
}
/** The server verifies the canonical payload digest and public UUID namespace. The browser
 * checks the display contract and compares the immutable version/hash on every revalidation;
 * this is not a client cryptographic attestation or source/fact verification. */
function validDetail(value: unknown, expectedSlug: string, expectedVersion?: number): value is PublicBriefingDetail {
  if (!isObject(value) || !hasKeys(value,[...summaryKeys,'canvas','source_titles','sources'])
    || !validSummary(value) || value.slug !== expectedSlug || (expectedVersion !== undefined && value.version !== expectedVersion)
    || !isObject(value.canvas) || !isObject(value.canvas.research) || !isObject(value.canvas.revision)
    || !isId(value.canvas.research.workspace_id) || !isId(value.canvas.revision.run_id)
    || !validResearchCanvas(value.canvas, value.canvas.research.workspace_id, value.canvas.revision.run_id, value.source_titles)
    || !Array.isArray(value.sources) || value.sources.length < 1 || value.sources.length > 5 || !isObject(value.source_titles)) return false;
  const detail = value as unknown as PublicBriefingDetail;
  if (detail.canvas.revision.draft.outcome !== 'answer') return false;
  const evidence = detail.canvas.research.evidence;
  if (new Set(evidence.map(item=>item.document.document_id)).size !== evidence.length || evidence.length !== detail.sources.length) return false;
  const sourceIds = new Set<string>();
  for (const source of value.sources) {
    if (!isObject(source) || !hasKeys(source,['document_id','official_url','title','publisher','published_on','license','attribution','text_sha256'])
      || !isId(source.document_id) || sourceIds.has(source.document_id) || !official(source.official_url)
      || !text(source.title,255) || isId(source.title) || !text(source.publisher,255) || !text(source.attribution,1000)
      || source.license !== 'kogl-type-1' || !hash(source.text_sha256) || !exactDay(source.published_on)
      || source.published_on > detail.as_of.slice(0,10) || detail.source_titles[source.document_id] !== source.title) return false;
    sourceIds.add(source.document_id);
    const proof = evidence.find(item=>item.document.document_id === source.document_id);
    if (!proof || proof.document.canonical_url !== source.official_url || proof.representation.text_sha256 !== source.text_sha256) return false;
  }
  let citationCount = 0;
  for (const proof of evidence) {
    const {document, version, representation, citations} = proof;
    if (!exact(proof,['schema_version','document','version','representation','citations'])
      || !exact(document,['document_id','workspace_id','provider','source_id','source_kind','canonical_url'])
      || !exact(version,['version_id','document_id','raw_object_id','raw_sha256','media_type','collected_at'])
      || !exact(representation,['representation_id','document_version_id','parser_name','parser_version','normalization_profile','text','text_sha256','pages','tables'])
      || document.provider !== 'public-reviewed-copy' || document.source_id !== document.document_id
      || representation.parser_name !== 'public-reviewed-copy' || representation.parser_version !== '1'
      || representation.normalization_profile !== 'public-reviewed-copy-v1' || !exactTimestamp(version.collected_at)
      || citations.length > 32 || !hash(representation.text_sha256) || !hash(version.raw_sha256)) return false;
    if (representation.pages.some(page=>!exact(page,['page_number','start','end']))) return false;
    for (const table of representation.tables) {
      if (!exact(table,['table_id','cells'])) return false;
      for (const cell of table.cells) {
        if (!exact(cell,['cell_id','text','unit','period','question','population','methodology','sample_size','weighting'])
          || [cell.unit,cell.period,cell.question,cell.population,cell.methodology,cell.weighting].some(item=>item !== null && typeof item !== 'string')
          || (cell.sample_size !== null && (typeof cell.sample_size !== 'number' || !Number.isSafeInteger(cell.sample_size) || cell.sample_size < 1))) return false;
      }
    }
    for (const citation of citations) {
      const selector=citation.selector;
      const keys=selector.kind==='table_cell'?['kind','table_id','cell_id','quote']:['kind','start','end','quote','prefix','suffix'];
      if (!exact(citation,['citation_id','document_version_id','representation_id','selector'])
        || !exact(selector,selector.kind==='pdf'?[...keys,'page_number','regions']:keys)
        || (selector.kind==='pdf' && selector.regions.some(box=>!exact(box,['x0','y0','x1','y1'])))) return false;
    }
    citationCount += citations.length;
  }
  return citationCount <= 100;
}
export function listPublicBriefings(options: PublicBriefingOptions = {}) {
  return protectedRequest('/api/v1/briefings','GET',validList,fail,options);
}
export function getPublicBriefing(publicSlug: string, publicVersion?: string | number, options: PublicBriefingOptions = {}) {
  if (!slug(publicSlug) || (publicVersion !== undefined && (typeof publicVersion === 'string' ? !/^[1-9][0-9]{0,15}$/.test(publicVersion) || !version(Number(publicVersion)) : !version(publicVersion)))) throw fail('malformed');
  const fixed = publicVersion === undefined ? undefined : Number(publicVersion);
  return protectedRequest(`/api/v1/briefings/${publicSlug}${fixed === undefined ? '' : `/versions/${fixed}`}`,'GET',
    (value): value is PublicBriefingDetail => validDetail(value,publicSlug,fixed),fail,options);
}
