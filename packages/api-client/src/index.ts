import type { components, paths } from './schema';

export type ServiceStatus = components['schemas']['ServiceStatus'];
export type StatusResult = { data: ServiceStatus; requestId: string };
export type ConnectionFailure = 'http' | 'invalid-response' | 'network' | 'timeout';

export class ConnectionError extends Error {
  constructor(public readonly kind: ConnectionFailure, public readonly requestId?: string) {
    super(`API connection failed: ${kind}`);
    this.name = 'ConnectionError';
  }
}

const expectedStatus = { service: 'issuedigest-api', api_version: 'v1', status: 'ok' } satisfies ServiceStatus;
const statusPath = '/api/v1/status' satisfies keyof paths;
const uuid = /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i;

function isStatus(value: unknown): value is ServiceStatus {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
  return Object.keys(value).length === Object.keys(expectedStatus).length
    && 'service' in value && value.service === expectedStatus.service
    && 'api_version' in value && value.api_version === expectedStatus.api_version
    && 'status' in value && value.status === expectedStatus.status;
}

/** Same-origin HTTP boundary. The deadline covers headers AND JSON body reading. */
export async function getStatus({ timeoutMs = 5000 }: { timeoutMs?: number } = {}): Promise<StatusResult> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let requestId: string | undefined;
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new ConnectionError('timeout', requestId));
    }, timeoutMs);
  });
  const request = async (): Promise<StatusResult> => {
    const response = await fetch(statusPath, {
      signal: controller.signal, credentials: 'same-origin', headers: { Accept: 'application/json' },
    });
    const header = response.headers.get('X-Request-ID');
    requestId = header && uuid.test(header) ? header : undefined;
    if (!response.ok) throw new ConnectionError('http', requestId);
    if (!requestId) throw new ConnectionError('invalid-response');
    let data: unknown;
    try { data = await response.json(); }
    catch { throw new ConnectionError('invalid-response', requestId); }
    if (!isStatus(data)) throw new ConnectionError('invalid-response', requestId);
    return { data, requestId };
  };
  try {
    return await Promise.race([request(), deadline]);
  } catch (error) {
    if (error instanceof ConnectionError) throw error;
    throw new ConnectionError(controller.signal.aborted ? 'timeout' : 'network', requestId);
  } finally {
    clearTimeout(timer);
  }
}

export { getCitationUtf16Range } from './citations';
export type SourceDocument = components['schemas']['SourceDocument'];
export type DocumentVersion = components['schemas']['DocumentVersion'];
export type ParsedRepresentation = components['schemas']['ParsedRepresentation'];
export type PageSpan = components['schemas']['PageSpan'];
export type ParsedTable = components['schemas']['ParsedTable'];
export type TableCell = components['schemas']['TableCell'];
export type TextQuoteSelector = components['schemas']['TextQuoteSelector'];
export type PdfQuoteSelector = components['schemas']['PdfQuoteSelector'];
export type NormalizedBox = components['schemas']['NormalizedBox'];
export type TableCellSelector = components['schemas']['TableCellSelector'];
export type Citation = components['schemas']['Citation'];
export type CitationAnchorValidation = components['schemas']['CitationAnchorValidation'];
export type EvidenceBundle = components['schemas']['EvidenceBundle'];

export type SourceIdentity = components['schemas']['SourceIdentity'];
export type Entity = components['schemas']['Entity'];
export type Claim = components['schemas']['Claim'];
export type DerivationRecord = components['schemas']['DerivationRecord'];
export type IdentityReview = components['schemas']['IdentityReview'];
export type SupportReview = components['schemas']['SupportReview'];
export type EntityReference = components['schemas']['EntityReference'];
export type ClaimReference = components['schemas']['ClaimReference'];
export type DocumentReference = components['schemas']['DocumentReference'];
export type RelationReference = components['schemas']['RelationReference'];
export type Relation = components['schemas']['Relation'];
export type DateInterval = components['schemas']['DateInterval'];
export type Dimension = components['schemas']['Dimension'];
export type ComparisonContext = components['schemas']['ComparisonContext'];
export type Observation = components['schemas']['Observation'];
export type ComparisonReason = components['schemas']['ComparisonReason'];
export type ComparisonAssessment = components['schemas']['ComparisonAssessment'];
export type ResearchBundle = components['schemas']['ResearchBundle'];

export type ExecutionVersions = components['schemas']['ExecutionVersions'];
export type RunInput = components['schemas']['RunInput'];
export type RunSubmission = components['schemas']['RunSubmission'];
export type Run = components['schemas']['Run'];
export type SubmissionAssessment = components['schemas']['SubmissionAssessment'];
export type RunEvent = components['schemas']['RunEvent'];
export type RunHistory = components['schemas']['RunHistory'];
export type RunSnapshot = components['schemas']['RunSnapshot'];
export type ReplayBatch = components['schemas']['ReplayBatch'];
export type CallAttempt = components['schemas']['CallAttempt'];
export type CanvasDraft = components['schemas']['CanvasDraft'];
export type CanvasRevision = components['schemas']['CanvasRevision'];
export type CanvasBundle = components['schemas']['CanvasBundle'];
export type PricingSnapshot = components['schemas']['PricingSnapshot'];
export type BudgetWindow = components['schemas']['BudgetWindow'];
export type UsageReservation = components['schemas']['UsageReservation'];
export type UsageEntry = components['schemas']['UsageEntry'];
export type UsageBook = components['schemas']['UsageBook'];
export type BudgetAssessment = components['schemas']['BudgetAssessment'];
export type RunExecutionBundle = components['schemas']['RunExecutionBundle'];
export type EvidenceModule = components['schemas']['EvidenceModule'];
export type SummaryModule = components['schemas']['SummaryModule'];
export type ComparisonModule = components['schemas']['ComparisonModule'];
export type TimelineModule = components['schemas']['TimelineModule'];
export type GraphModule = components['schemas']['GraphModule'];
export type ChartModule = components['schemas']['ChartModule'];
export type OpenEvidenceAction = components['schemas']['OpenEvidenceAction'];
export type SelectDocumentAction = components['schemas']['SelectDocumentAction'];
export type AskQuestionAction = components['schemas']['AskQuestionAction'];
export type SortAction = components['schemas']['SortAction'];
export type CanvasModule = components['schemas']['ModuleReadyPayload']['module'];
export type CanvasAction = EvidenceModule['actions'][number];
export type RunEventPayload = RunEvent['payload'];
export type MoneyMicrowon = BudgetAssessment['used_microwon'];

export { getEvidence, EvidenceError } from './evidence';
export type { EvidenceFailure, EvidenceOptions, EvidenceResult } from './evidence';
export { getSession, logout, AuthError } from './auth';
export type { SessionInfo, WorkspaceMembership, AuthFailure, AuthOptions } from './auth';
export { searchEvidence, SearchError } from './search';
export type { EvidenceSearchQuery, EvidenceSearchResult, EvidenceSearchHit, EvidenceSearchInput, SearchFailure, SearchOptions } from './search';
export { resolveSearchSelection } from './search-selection';
export type { SearchSelection } from './search-selection';
export { listResearchRuns, getResearchRun, submitResearch, cancelResearchRun, ResearchError } from './research';
export type { ResearchRun, ResearchRunList, ResearchRequest, ResearchOptions, ResearchFailure } from './research';
export {listPublicBriefings, getPublicBriefing, PublicBriefingError} from './briefings';
export type {PublicBriefingSummary, PublicBriefingDetail, PublicBriefingList, PublicSourceAttribution, PublicBriefingOptions, PublicBriefingFailure, PublicBriefingErrorResponse} from './briefings';

export {validResearchClassifications, claimClassification} from './research-classification';
export {getBriefingJob,cancelBriefingJob,BriefingJobError} from './briefing-jobs';
export type {BriefingJobView,BriefingQuoteView,BriefingJobOptions} from './briefing-jobs';
export {submitQuestion,listBriefingJobs,QuestionError} from './question-submissions';
export type {QuestionRequest,QuestionResult,BriefingJobList} from './question-submissions';
