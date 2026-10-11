/** Compile-only consumers of the actual generated execution/canvas/usage contracts. */
import type {
  ExecutionVersions, RunInput, RunSubmission, Run, SubmissionAssessment, RunEvent,
  RunHistory, RunSnapshot, ReplayBatch, CallAttempt, CanvasDraft, CanvasRevision,
  CanvasBundle, PricingSnapshot, BudgetWindow, UsageReservation, UsageEntry,
  UsageBook, BudgetAssessment, RunExecutionBundle, CanvasModule, CanvasAction,
  RunEventPayload, MoneyMicrowon,
} from '../src/index';
import type { components } from '../src/schema';

type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;
type Assert<T extends true> = T;
export type PublicGeneratedTypes = Assert<Equal<
  [ExecutionVersions, RunInput, RunSubmission, Run, SubmissionAssessment, RunEvent,
    RunHistory, RunSnapshot, ReplayBatch, CallAttempt, CanvasDraft, CanvasRevision,
    CanvasBundle, PricingSnapshot, BudgetWindow, UsageReservation, UsageEntry,
    UsageBook, BudgetAssessment, RunExecutionBundle],
  [components['schemas']['ExecutionVersions'], components['schemas']['RunInput'],
    components['schemas']['RunSubmission'], components['schemas']['Run'],
    components['schemas']['SubmissionAssessment'], components['schemas']['RunEvent'],
    components['schemas']['RunHistory'], components['schemas']['RunSnapshot'],
    components['schemas']['ReplayBatch'], components['schemas']['CallAttempt'],
    components['schemas']['CanvasDraft'], components['schemas']['CanvasRevision'],
    components['schemas']['CanvasBundle'], components['schemas']['PricingSnapshot'],
    components['schemas']['BudgetWindow'], components['schemas']['UsageReservation'],
    components['schemas']['UsageEntry'], components['schemas']['UsageBook'],
    components['schemas']['BudgetAssessment'], components['schemas']['RunExecutionBundle']]
>>;

export const exactMoney: MoneyMicrowon = '123456789012345678901234567890';
export const unknownCost: UsageEntry['cost_microwon'] = null;
export const bar: CanvasModule = { kind: 'chart', module_id: 'id', title: '제공 수치', span: 'half',
  citation_ids: ['citation'], actions: [], chart_type: 'bar', observation_ids: ['first', 'second'] };
export const proposedQuestion: CanvasAction = { kind: 'ask_question', question: '이 근거는?' };
export const moduleReady: RunEventPayload = { kind: 'module.ready', revision_id: 'revision', module: bar };
// @ts-expect-error money remains an integer string on the public transport boundary
export const floatingMoney: MoneyMicrowon = 1.5;
// @ts-expect-error module has no arbitrary executable HTML field
export const htmlModule: CanvasModule = { ...bar, html: '<script>' };
// @ts-expect-error only bar charts are allowed
export const pieChart: CanvasModule = { ...bar, chart_type: 'pie' };
// @ts-expect-error module.ready carries a complete typed module
export const incompleteReady: RunEventPayload = { kind: 'module.ready', revision_id: 'revision' };
// @ts-expect-error UI actions do not execute tools
export const toolAction: CanvasAction = { kind: 'execute', tool: 'x' };
// @ts-expect-error event payload has no raw exception field
export const rawException: RunEventPayload = { kind: 'run.failed', error_code: 'internal_error', retryable: true, exception: 'stack' };
