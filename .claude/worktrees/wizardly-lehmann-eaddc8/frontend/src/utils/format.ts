/**
 * 中文习惯大数字展示：万 / K；亿级单独处理。
 */
export function formatNumber(n: number | null | undefined): string {
  if (n == null || Number.isNaN(Number(n))) return "0";
  const v = Number(n);
  const ax = Math.abs(v);
  if (ax >= 1e8) {
    return `${(v / 1e8).toFixed(1)}亿`;
  }
  if (ax >= 1e4) {
    return `${(v / 1e4).toFixed(1)}万`;
  }
  if (ax >= 1e3) {
    return `${(v / 1e3).toFixed(1)}K`;
  }
  return String(Math.round(v));
}
