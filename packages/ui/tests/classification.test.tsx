import {render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {describe, expect, test} from 'vitest';
import {CanvasView} from '../src';
import {classifiedRun} from '../../api-client/tests/classification-data';
import legacy from '../../api-client/tests/fixtures/research-run-generated.json';
import type {CanvasBundle} from '@issuedigest/api-client';

test.each([
  ['documented', '자료에 기록됨'], ['attributed', '출처의 주장'], ['uncertain', '확인하기 어려움'],
] as const)('explains %s on keyboard and click while retaining AI interpretation and exact source actions', async (category, label) => {
  const value = classifiedRun(category).result!;
  const actions: unknown[] = [];
  render(<CanvasView bundle={value.canvas} presentation="briefing" sourceTitles={value.source_titles} onAction={action => actions.push(action)}/>);
  expect(screen.getByText('AI 해석')).toBeInTheDocument();
  const summary = screen.getByText(label);
  expect(summary.tagName).toBe('SUMMARY');
  expect(summary).toHaveAttribute('title', expect.stringContaining('독립적인 사실 검증'));
  expect(summary.closest('details')).not.toHaveAttribute('open');
  summary.focus();
  expect(summary).toHaveFocus();
  await userEvent.setup().click(summary);
  expect(summary.closest('details')).toHaveAttribute('open');
  expect(screen.getByText(/선택한 인용에 대한 합성 AI 설명/)).toBeVisible();
  expect(screen.getByText(/선택한 인용에 대한 AI 평가/)).toBeVisible();
  await userEvent.setup().click(screen.getAllByRole('button', {name:/근거 열기/})[0]!);
  expect(actions).toEqual([{kind:'open_evidence', citation_id:value.canvas.research.claims[0]!.citation_ids[0]}]);
});

test('saved legacy results retain AI interpretation without assigning a new category', () => {
  render(<CanvasView bundle={structuredClone(legacy.result.canvas) as CanvasBundle} sourceTitles={legacy.result.source_titles}/>);
  expect(screen.getByText('AI 해석')).toBeInTheDocument();
  for (const label of ['자료에 기록됨', '출처의 주장', '확인하기 어려움']) expect(screen.queryByText(label)).not.toBeInTheDocument();
});

test.each(['missing', 'mixed', 'bad-target'] as const)('rejects %s classification when renderer receives a malformed typed object', kind => {
  const result = classifiedRun().result!;
  if (kind === 'missing') result.canvas.research.support_reviews = [];
  if (kind === 'mixed') result.canvas.research.claims[0]!.derivation!.method_version = 'research-v2';
  if (kind === 'bad-target') result.canvas.research.support_reviews[0]!.target = {kind:'claim', claim_id:'00000000-0000-4000-8000-000000000999'};
  render(<CanvasView bundle={result.canvas} sourceTitles={result.source_titles}/>);
  expect(screen.getByRole('alert')).toBeInTheDocument();
  expect(screen.queryByText('자료에 기록됨')).not.toBeInTheDocument();
});

describe.each(['v4', 'v5'] as const)('%s', version => {
test('uses the existing attribution explanation and exact source action', async () => {
  const result = classifiedRun('attributed', version).result!;
  const actions: unknown[] = [];
  render(<CanvasView bundle={result.canvas} sourceTitles={result.source_titles} onAction={action => actions.push(action)}/>);
  expect(screen.getByText('AI 해석')).toBeInTheDocument();
  await userEvent.setup().click(screen.getByText('출처의 주장'));
  expect(screen.getByText(/선택한 인용에 대한 합성 AI 설명/)).toBeVisible();
  await userEvent.setup().click(screen.getAllByRole('button', {name:/근거 열기/})[0]!);
  expect(actions).toEqual([{kind:'open_evidence', citation_id:result.canvas.research.claims[0]!.citation_ids[0]}]);
});
test.each(['missing', 'mixed', 'reviewer', 'microsecond', 'citation'] as const)('rejects invalid display: %s', kind => {
  const result = classifiedRun('documented', version).result!, research = result.canvas.research;
  if (kind === 'missing') research.support_reviews = [];
  if (kind === 'mixed') research.claims[0]!.derivation!.method_version = 'research-v3';
  if (kind === 'reviewer') research.support_reviews[0]!.reviewer_id = 'issuedigest-research-v3';
  if (kind === 'microsecond') research.support_reviews[0]!.reviewed_at = '2026-10-13T00:00:00.123457Z';
  if (kind === 'citation') research.support_reviews[0]!.citation_ids.reverse().push(research.evidence[0]!.citations[1]!.citation_id);
  render(<CanvasView bundle={result.canvas} sourceTitles={result.source_titles}/>);
  expect(screen.getByRole('alert')).toBeInTheDocument();
});

});
