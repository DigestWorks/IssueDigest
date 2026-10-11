import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import * as apiClient from '../src/index';
import type { components } from '../src/schema';

type QuoteSelector = components['schemas']['TextQuoteSelector'] | components['schemas']['PdfQuoteSelector'];
const fixture = JSON.parse(readFileSync(new URL('../../../tests/fixtures/citation-unicode.json', import.meta.url), 'utf8')) as {
  synthetic: boolean; text: string; cases: { selector: QuoteSelector; utf16_range: { start: number; end: number } }[];
};

describe('citation code point to UTF-16 boundary', () => {
  it.each(fixture.cases)('selects the shared Unicode quote exactly: $selector.quote', ({ selector, utf16_range }) => {
    expect(apiClient).toHaveProperty('getCitationUtf16Range');
    const range = apiClient.getCitationUtf16Range(fixture.text, selector);
    expect(range).toEqual(utf16_range);
    expect(fixture.text.slice(range.start, range.end)).toBe(selector.quote);
  });
});

const base = fixture.cases[0].selector;
it.each([
  { start: -1 }, { start: true }, { start: 2.5 }, { start: '2' }, { start: NaN },
  { end: 2 }, { end: true }, { end: 7.5 }, { end: '7' }, { end: Infinity }, { end: 99 },
  { quote: '' }, { quote: '😀한éé' }, { quote: '😀한e\u0301é ' }, { quote: 1 },
  { prefix: '앞 ' }, { prefix: 'too long prefix' }, { prefix: true },
  { suffix: '뒤 ' }, { suffix: ' 뒤 too long' }, { suffix: 1 },
  { kind: 'table_cell' }, { kind: 'unknown' },
  { kind: 'pdf', page_number: 0 }, { kind: 'pdf', page_number: true },
  { kind: 'pdf', page_number: '1' }, { kind: 'pdf', page_number: 1.5 },
])('rejects invalid citation conversion input: %j', (patch) => {
  const selector = { ...base, ...patch } as unknown as QuoteSelector;
  expect(() => apiClient.getCitationUtf16Range(fixture.text, selector)).toThrow();
});

it('accepts empty edge contexts and adjacent partial contexts without trimming', () => {
  expect(apiClient.getCitationUtf16Range(fixture.text, { kind: 'text', start: 0, end: 2, quote: ' 앞', prefix: '', suffix: '😀' })).toEqual({ start: 0, end: 2 });
  expect(apiClient.getCitationUtf16Range(fixture.text, { ...base, prefix: '앞', suffix: ' 뒤' })).toEqual({ start: 2, end: 8 });
});

it('rejects a missing selector discriminant at the runtime boundary', () => {
  const selector = { start: 2, end: 3, quote: '😀' } as unknown as QuoteSelector;
  expect(() => apiClient.getCitationUtf16Range(fixture.text, selector)).toThrow();
});

it.each([null, undefined, 42, [], {}])('rejects malformed runtime selector: %j', (selector) => {
  expect(() => apiClient.getCitationUtf16Range(fixture.text, selector as unknown as QuoteSelector)).toThrow();
});
