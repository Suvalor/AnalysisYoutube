/** 由 YouTube 视频 ID 生成标准播放页链接；非法或为空时返回 null */
export function buildYouTubeWatchUrl(ytVideoId: string | null | undefined): string | null {
  const id = (ytVideoId ?? "").trim();
  if (!id) return null;
  // 避免注入：仅允许常见视频 ID 字符（YouTube 视频 ID 一般为 11 位字母数字与 -_）
  if (!/^[a-zA-Z0-9_-]{6,32}$/.test(id)) return null;
  return `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
}
