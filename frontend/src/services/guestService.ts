import apiClient from "./apiClient";
import type { QuotaUsage } from "@/types/auth";

/**
 * 获取游客配额使用情况。
 * 后端通过 Cookie（HttpOnly）或 IP 识别游客，前端无需手动携带 guest_id。
 */
export async function fetchGuestQuotaUsage(): Promise<QuotaUsage> {
  const res = await apiClient.get<QuotaUsage>("/api/quota/usage");
  return res.data;
}

/**
 * 检查游客配额是否已用完。
 * limit=0 表示该类 API 不开放，limit<0 表示无限制；两者都不计入耗尽判断。
 * 返回 true 表示至少有一类已开放的配额已达到上限。
 */
export function isGuestQuotaExhausted(usage: QuotaUsage): boolean {
  const youtubeExhausted = usage.youtube_api_limit > 0 && usage.youtube_api_used >= usage.youtube_api_limit;
  const llmExhausted = usage.llm_api_limit > 0 && usage.llm_api_used >= usage.llm_api_limit;
  const cvExhausted = usage.cv_api_limit > 0 && usage.cv_api_used >= usage.cv_api_limit;
  return youtubeExhausted || llmExhausted || cvExhausted;
}
