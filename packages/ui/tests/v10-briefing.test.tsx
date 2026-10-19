import {render, screen, within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {expect, test} from 'vitest';
import {CanvasView} from '../src';
import {prepareCanvas} from '../src/prepare';
import type {CanvasBundle} from '@issuedigest/api-client';
import fixture from '../../api-client/tests/fixtures/research-run-v10-generated.json';

const canvas = () => structuredClone(fixture.result.canvas) as CanvasBundle;
test.each(['missing', 'mixed', 'reviewer', 'all-uncertain', 'other-subject'] as const)('rejects malformed v10 display %s', mutation => {
  const value = canvas(), research = value.research;
  if (mutation === 'missing') research.support_reviews = [];
  if (mutation === 'mixed') research.claims[0]!.derivation!.method_version = 'research-v5';
  if (mutation === 'reviewer') research.support_reviews[0]!.reviewer_id = 'issuedigest-research-v5';
  if (mutation === 'all-uncertain') research.support_reviews.forEach(review => Object.assign(review, {scope:'content', assessment:'insufficient'}));
  if (mutation === 'other-subject') research.claims[0]!.text = '다른 기관에 따르면, 같은 방향입니다.';
  expect(prepareCanvas(value)).toEqual({status:'rejected'});
  render(<CanvasView bundle={value} presentation="briefing"/>);
  expect(screen.getByRole('alert')).toBeInTheDocument();
});
test('renders a nonanswer with fixed insufficient heading and a cited-material scope message', () => {
  const value = canvas();
  value.research.claims = []; value.research.support_reviews = [];
  Object.assign(value.revision.draft, {outcome:'insufficient_evidence', modules:[], message:'제공 자료로 핵심 질문에 답할 근거가 부족합니다.'});
  render(<CanvasView bundle={value} presentation="briefing"/>);
  expect(screen.getByRole('status')).toHaveTextContent('근거가 부족합니다');
  expect(screen.getByText('제공 자료로 핵심 질문에 답할 근거가 부족합니다.')).toBeVisible();
  expect(screen.queryByRole('blockquote')).not.toBeInTheDocument();
});


test('shows the Python v10 core first, folds details, and opens the exact selected quote', async () => {
  const value = canvas(), actions: unknown[] = [];
  render(<CanvasView bundle={value} presentation="briefing" sourceTitles={fixture.result.source_titles} onAction={action => actions.push(action)}/>);
  const summary = screen.getByRole('article').querySelector('section')!;
  expect(summary).toHaveAccessibleName('합성 비교 결론');
  expect(within(summary).getByText('제공 자료에 따르면, 두 합성 지표는 같은 방향입니다.')).toBeVisible();
  const detail = screen.getByText('합성 비교 상세');
  expect(detail.closest('details')).not.toHaveAttribute('open');
  await userEvent.setup().click(detail);
  expect(detail.closest('details')).toHaveAttribute('open');
  const proof = value.research.evidence[0]!.citations[0]!;
  await userEvent.setup().click(within(summary).getAllByRole('button', {name:/근거 열기/})[0]!);
  expect(actions).toEqual([{kind:'open_evidence', citation_id:proof.citation_id}]);
  expect(value.research.evidence[0]!.representation.text.slice(proof.selector.kind === 'text' ? proof.selector.start : 0,
    proof.selector.kind === 'text' ? proof.selector.end : 0)).toBe(proof.selector.quote);
  expect(within(summary).getAllByText('AI 해석')[0]).toBeVisible();
  await userEvent.setup().click(screen.getByText('근거', {selector:'summary'}));
  expect(screen.getByRole('blockquote')).toHaveTextContent(proof.selector.quote);
});

test('shows the exact source date only in collapsed timeline detail and opens its citation', async () => {
  const {default: fixture} = await import('../../api-client/tests/fixtures/research-run-v10-timeline-generated.json');
  const value = structuredClone(fixture.result.canvas) as CanvasBundle, actions: unknown[] = [];
  render(<CanvasView bundle={value} presentation="briefing" onAction={action => actions.push(action)}/>);
  expect(screen.getByText('제공 자료에 따르면, 두 합성 지표는 같은 방향입니다.')).toBeVisible();
  const detail = screen.getByText('합성 날짜 상세');
  expect(detail.closest('details')).not.toHaveAttribute('open');
  await userEvent.setup().click(detail);
  expect(screen.getByText('2026-10-19')).toBeVisible();
  await userEvent.setup().click(within(detail.closest('details')!).getAllByRole('button', {name:/근거 열기/})[0]!);
  expect(actions).toEqual([{kind:'open_evidence', citation_id:value.research.evidence[0]!.citations[0]!.citation_id}]);
});
