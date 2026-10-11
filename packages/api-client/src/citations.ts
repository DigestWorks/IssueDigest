import type { components } from './schema';

/** Validate an exact quote, then convert code point offsets to JS UTF-16 indices.
 * This preserves whitespace and normalization; boundaries are not grapheme clusters.
 * PDF page spans and semantic support require the server's representation validation.
 */
export function getCitationUtf16Range(
  text: string,
  selector: components['schemas']['TextQuoteSelector'] | components['schemas']['PdfQuoteSelector'],
): { start: number; end: number } {
  if (typeof text !== 'string' || typeof selector !== 'object' || selector === null || Array.isArray(selector)) {
    throw new Error('Citation text and selector have invalid types');
  }
  if (selector.kind !== 'text' && selector.kind !== 'pdf') {
    throw new Error('Only text and PDF quotes have character ranges');
  }
  if (selector.kind === 'pdf' || 'page_number' in selector) {
    if (!('page_number' in selector) || typeof selector.page_number !== 'number' || !Number.isSafeInteger(selector.page_number) || selector.page_number < 1) {
      throw new Error('PDF page_number must be a positive integer');
    }
  }
  const points = Array.from(text);
  const { start, end, quote, prefix, suffix } = selector;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || end <= start || end > points.length) {
    throw new Error('Citation code point range is invalid');
  }
  if (typeof quote !== 'string' || quote.length === 0 || points.slice(start, end).join('') !== quote) {
    throw new Error('Citation quote does not match text');
  }
  if (prefix !== undefined && prefix !== null) {
    if (typeof prefix !== 'string') throw new Error('Citation prefix must be a string');
    const contextStart = start - Array.from(prefix).length;
    if (contextStart < 0 || points.slice(contextStart, start).join('') !== prefix) {
      throw new Error('Citation prefix does not match adjacent text');
    }
  }
  if (suffix !== undefined && suffix !== null) {
    if (typeof suffix !== 'string') throw new Error('Citation suffix must be a string');
    const contextEnd = end + Array.from(suffix).length;
    if (contextEnd > points.length || points.slice(end, contextEnd).join('') !== suffix) {
      throw new Error('Citation suffix does not match adjacent text');
    }
  }
  return {
    start: points.slice(0, start).join('').length,
    end: points.slice(0, end).join('').length,
  };
}
