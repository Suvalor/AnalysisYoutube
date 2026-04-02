import apiClient from "@/services/apiClient";

export type FeishuDocItem = {
  id: number;
  title: string;
  url: string;
  org_id: number;
  created_at: string;
};

export type FeishuDocListResponse = {
  items: FeishuDocItem[];
  total: number;
  page: number;
  page_size: number;
};

export async function listFeishuDocsApi(params: { page: number; page_size: number; search?: string }) {
  const searchParams = new URLSearchParams();
  searchParams.append("page", String(params.page));
  searchParams.append("page_size", String(params.page_size));
  if (params.search && params.search.trim()) searchParams.append("search", params.search.trim());
  const res = await apiClient.get(`/api/feishu_docs?${searchParams.toString()}`);
  return res.data as FeishuDocListResponse;
}

export async function createFeishuDocApi(payload: { title: string; url: string }) {
  const res = await apiClient.post("/api/feishu_docs", payload);
  return res.data as FeishuDocItem;
}

export async function deleteFeishuDocApi(id: number) {
  const res = await apiClient.delete(`/api/feishu_docs/${id}`);
  return res.data as { success: boolean };
}

export async function getFeishuDocApi(id: number) {
  const res = await apiClient.get(`/api/feishu_docs/${id}`);
  return res.data as FeishuDocItem;
}

