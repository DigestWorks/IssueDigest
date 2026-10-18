/** Exact Gregorian dates and UTC timestamps, with up to six fractional digits. */
export function exactDay(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, date] = value.split('-').map(Number);
  const leap = year! % 4 === 0 && (year! % 100 !== 0 || year! % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return year! > 0 && month! >= 1 && month! <= 12 && date! >= 1 && date! <= days[month! - 1]!;
}

export function exactTimestamp(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const parts = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(?:Z|\+00:00)$/.exec(value);
  return parts !== null && exactDay(parts[1]) && Number(parts[2]) < 24
    && Number(parts[3]) < 60 && Number(parts[4]) < 60 && Number.isFinite(Date.parse(value));
}
