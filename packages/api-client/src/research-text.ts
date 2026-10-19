/** v6 only: union of Python Unicode whitespace and ECMAScript WhiteSpace/LineTerminator. */
// eslint-disable-next-line no-control-regex -- the v6 contract explicitly includes control whitespace
const v6Nonblank = /[^\u0009-\u000D\u001C-\u0020\u0085\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF]/u;

/** Check presence without trimming, normalizing or changing stored text. */
export function hasV6Text(value: string): boolean {
  return v6Nonblank.test(value);
}
