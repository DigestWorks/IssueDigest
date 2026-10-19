import {render, screen} from '@testing-library/react';
import {expect, test} from 'vitest';
import {CanvasView} from '../src';
import {prepareCanvas} from '../src/prepare';
import type {CanvasBundle} from '@issuedigest/api-client';
import fixture from '../../api-client/tests/fixtures/research-run-v6-generated.json';

const canvas = () => structuredClone(fixture.result.canvas) as CanvasBundle;
test.each(['missing', 'mixed', 'reviewer', 'all-uncertain', 'other-subject'] as const)('rejects malformed v6 display %s', mutation => {
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
