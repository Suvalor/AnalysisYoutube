import apiClient from "./apiClient";

export type InspirationItem = {
  id: number;
  user_id: number;
  content: string;
  image_url: string | null;
  image_asset_id: number | null;
  /** 后端签名 URL，私有桶展示用 */
  image_access_url: string | null;
  source: string;
  recorded_at: string;
  status: string;
  plot_id: number | null;
  created_at: string;
  updated_at: string;
};

/** 与后端纯图片灵感占位正文一致 */
export const INSPIRATION_IMAGE_PLACEHOLDER = "（图片灵感）";

/** 生成进入 SOP 剧情拆解用的剧本大纲：包含正文与 Markdown 图片语法及 URL 文本，便于模型理解 */
export function buildScriptOutlineFromInspiration(row: InspirationItem): string {
  const url = (row.image_access_url || row.image_url || "").trim();
  const textRaw = (row.content || "").trim();
  const text = textRaw === INSPIRATION_IMAGE_PLACEHOLDER ? "" : textRaw;
  const parts: string[] = [];
  if (text) parts.push(text);
  if (url) {
    if (parts.length) parts.push("");
    parts.push(`![灵感参考图](${url})`);
    parts.push("");
    parts.push(`（图片地址：${url}）`);
  }
  return parts.join("\n").trim() || (url ? `![灵感参考图](${url})` : "");
}

export type InspirationCreatePayload = {
  content?: string;
  image_url?: string | null;
  /** 上传素材接口返回的 id，与 image_url 二选一（新流程推荐） */
  image_asset_id?: number | null;
  source?: string;
  /** ISO 字符串，可选 */
  recorded_at?: string | null;
};

export async function listInspirationsApi() {
  const res = await apiClient.get("/api/inspirations");
  return res.data as InspirationItem[];
}

export async function createInspirationApi(payload: InspirationCreatePayload) {
  const res = await apiClient.post("/api/inspirations", payload);
  return res.data as InspirationItem;
}

export async function updateInspirationApi(
  inspirationId: number,
  payload: Partial<InspirationCreatePayload> & { status?: string }
) {
  const res = await apiClient.put(`/api/inspirations/${inspirationId}`, payload);
  return res.data as InspirationItem;
}

export async function deleteInspirationApi(inspirationId: number) {
  await apiClient.delete(`/api/inspirations/${inspirationId}`);
}

export async function linkInspirationPlotApi(inspirationId: number, body: { plot_id: number }) {
  const res = await apiClient.post(`/api/inspirations/${inspirationId}/link-plot`, body);
  return res.data as InspirationItem;
}
