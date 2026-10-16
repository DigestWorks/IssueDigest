import { afterEach, expect, it, vi } from 'vitest';
import { clearGuestQuestionDraft, consumeGuestQuestionDraft, readGuestQuestionDraft, writeGuestQuestionDraft } from '../app/guest-question';

const key = 'issuedigest.guest-question.v1';
const now = 1_790_000_000_000;
afterEach(() => { vi.restoreAllMocks(); sessionStorage.removeItem(key); sessionStorage.removeItem('unrelated'); });
function seed(value: unknown) { sessionStorage.setItem(key, JSON.stringify(value)); }

it('stores only a bounded question and timestamp and consumes it once', () => {
  vi.spyOn(Date, 'now').mockReturnValue(now);
  expect(writeGuestQuestionDraft('  어떤 변화가 있나요?  ')).toBe(true);
  expect(JSON.parse(sessionStorage.getItem(key)!)).toEqual({version: 1, question: '어떤 변화가 있나요?', createdAt: now});
  expect(readGuestQuestionDraft()).toBe('어떤 변화가 있나요?');
  expect(consumeGuestQuestionDraft()).toBe('어떤 변화가 있나요?');
  expect(consumeGuestQuestionDraft()).toBeNull();
});
it.each(['', '   ', '가'.repeat(1501)])('rejects empty or overlong input without replacing a valid draft', question => {
  writeGuestQuestionDraft('유효한 질문');
  expect(writeGuestQuestionDraft(question)).toBe(false);
  expect(readGuestQuestionDraft()).toBe('유효한 질문');
});
it('accepts 1500 characters and remains valid just before the thirty minute limit', () => {
  vi.spyOn(Date, 'now').mockReturnValue(now);
  expect(writeGuestQuestionDraft('가'.repeat(1500))).toBe(true);
  vi.spyOn(Date, 'now').mockReturnValue(now + 30 * 60_000 - 1);
  expect(readGuestQuestionDraft()).toHaveLength(1500);
});
it.each([
  {version: 1, question: '질문', createdAt: now - 30 * 60_000},
  {version: 1, question: '질문', createdAt: now + 1},
  {version: 1, question: '질문', createdAt: null},
  {version: 1, question: '질문', createdAt: '1790000000000'},
  {version: 2, question: '질문', createdAt: now},
  {version: 1, question: '   ', createdAt: now},
  {version: 1, question: '가'.repeat(1501), createdAt: now},
  null, [],
])('removes invalid or expired data while preserving other storage', value => {
  vi.spyOn(Date, 'now').mockReturnValue(now); sessionStorage.setItem('unrelated', 'keep'); seed(value);
  expect(readGuestQuestionDraft()).toBeNull(); expect(sessionStorage.getItem(key)).toBeNull();
  expect(sessionStorage.getItem('unrelated')).toBe('keep');
});
it.each(['{broken', '{"version":1,"question":"질문","createdAt":1e999}', ' '.repeat(12001)])('rejects corrupted, infinite or overlong raw JSON', raw => {
  sessionStorage.setItem(key, raw); expect(readGuestQuestionDraft()).toBeNull(); expect(sessionStorage.getItem(key)).toBeNull();
});
it('clears only the guest question key', () => {
  writeGuestQuestionDraft('지워질 질문'); sessionStorage.setItem('unrelated', 'keep'); clearGuestQuestionDraft();
  expect(readGuestQuestionDraft()).toBeNull(); expect(sessionStorage.getItem('unrelated')).toBe('keep');
});
it('does not throw when the browser refuses storage', () => {
  vi.spyOn(window, 'sessionStorage', 'get').mockImplementation(() => { throw new DOMException('blocked', 'SecurityError'); });
  expect(writeGuestQuestionDraft('질문')).toBe(false); expect(readGuestQuestionDraft()).toBeNull(); expect(consumeGuestQuestionDraft()).toBeNull();
  expect(() => clearGuestQuestionDraft()).not.toThrow();
});
it('does not hand off a draft if consume cannot remove it', () => {
  writeGuestQuestionDraft('한 번만 복원'); vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('blocked'); });
  expect(consumeGuestQuestionDraft()).toBeNull();
});
it('tolerates server rendering without browser storage', () => {
  vi.stubGlobal('window', undefined);
  expect(writeGuestQuestionDraft('질문')).toBe(false); expect(readGuestQuestionDraft()).toBeNull(); expect(consumeGuestQuestionDraft()).toBeNull(); expect(() => clearGuestQuestionDraft()).not.toThrow();
  vi.unstubAllGlobals();
});
