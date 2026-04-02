import apiClient from "./apiClient";

export type InspirationItem = {
  id: number;
  user_id: number;
  content: string;
  source: string;
  recorded_at: string;
  status: string;
  plot_id: number | null;
  created_at: string;
  updated_at: string;
};

export type InspirationCreatePayload = {
  content: string;
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

export async function updateInspirationApi(inspirationId: number, payload: Partial<InspirationCreatePayload> & { status?: string }) {
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
