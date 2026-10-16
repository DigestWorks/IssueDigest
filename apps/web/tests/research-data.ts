import fixture from '../../../tests/fixtures/canvas-synthetic.json';
import type {CanvasBundle, ResearchRun} from '@issuedigest/api-client';
import {workspace, snapshot} from './workspace-data';
export const source = { snapshot_id: snapshot, document_id: '00000000-0000-4000-8000-000000000002', title: '공공기록법 일부개정법률안', source_kind: 'bill', bill_number: '2201234', proposed_on: '2024-09-02', collected_at: '2026-10-13T00:00:00Z', canonical_url: null, citation_count: 2, excerpt: '제안 이유의 일부' };
export const secondSource = {...source, snapshot_id: '00000000-0000-4000-8000-000000000098', document_id: '00000000-0000-4000-8000-000000000003', title: '두 번째 법안', bill_number:'2209999', excerpt:''};
export const session = { schema_version: 1, user_id: snapshot, memberships: [{ workspace_id: workspace, role: 'owner' }] };
export const runId = '00000000-0000-4000-8000-000000000040';
export const now = '2026-10-15T00:00:00Z';
export function completedRun(): ResearchRun {
  const canvas = structuredClone(fixture) as CanvasBundle;
  const proof = canvas.research.evidence[0];
  proof.citations = [proof.citations[0]];
  canvas.research.evidence = [proof];
  canvas.research.claims = [{claim_id: '00000000-0000-4000-8000-000000000041', workspace_id: workspace, text: '합성 근거에 맞춘 AI 해석', basis: 'inference', speaker_entity_id: null, subject_entity_ids: [], citation_ids: [proof.citations[0].citation_id], valid_period: null, raw_event_time_text: null, derivation: {method: 'pydantic-ai', method_version: 'research-v1', rationale: '인용에 기반한 해석'}}];
  canvas.research.entities = []; canvas.research.relations = []; canvas.research.observations = []; canvas.research.support_reviews = [];
  canvas.revision.run_id = runId; canvas.revision.selected_version_ids = [proof.version.version_id];
  canvas.revision.draft.modules = [
    {kind: 'summary', module_id: '00000000-0000-4000-8000-000000000042', title: '핵심 정리', span: 'full', claim_ids: [canvas.research.claims[0].claim_id], citation_ids: [proof.citations[0].citation_id], actions: [{kind: 'open_evidence', citation_id: proof.citations[0].citation_id}]},
    {kind: 'evidence', module_id: '00000000-0000-4000-8000-000000000043', title: '근거', span: 'full', citation_ids: [proof.citations[0].citation_id], actions: [{kind: 'open_evidence', citation_id: proof.citations[0].citation_id}]},
  ];
  return {run_id: runId, workspace_id: workspace, request_id: '00000000-0000-4000-8000-000000000044', question: '법안의 핵심은?', snapshot_ids: [snapshot], parent_run_id: null, status: 'completed', error_code: null, created_at: now, updated_at: now, model: 'gpt-5.4-mini', input_tokens: 100, output_tokens: 50, events: [{sequence: 1, status: 'queued', created_at: now}, {sequence: 2, status: 'completed', created_at: now}], result: {canvas, source_titles: {[proof.document.document_id]: source.title}}} as ResearchRun;
}
export function queuedRun(request: Record<string, unknown>): ResearchRun {
  return {...completedRun(), request_id: request.request_id as string, question: request.question as string, snapshot_ids: (request.snapshot_ids as string[] | undefined) ?? [], parent_run_id: request.parent_run_id as string | null, status: 'queued', result: null, input_tokens: 0, output_tokens: 0, events: [{sequence: 1, status: 'queued', created_at: now}]};
}
