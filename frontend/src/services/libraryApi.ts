import apiClient from "./apiClient";

export type PromptItem = {
  id: number;
  user_id: number;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type StyleItem = {
  id: number;
  user_id: number;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type ScriptItem = {
  id: number;
  user_id: number;
  title: string;
  content: string;
  prompt_id: number | null;
  style_id: number | null;
  created_at: string;
  updated_at: string;
};

export type AssetItem = {
  id: number;
  user_id: number;
  title: string;
  file_type: "image" | "video" | "audio";
  file_url: string;
  created_at: string;
  updated_at: string;
};

export async function listPromptsApi() {
  const res = await apiClient.get("/api/libraries/prompts");
  return res.data as PromptItem[];
}

export async function listStylesApi() {
  const res = await apiClient.get("/api/libraries/styles");
  return res.data as StyleItem[];
}

export async function createScriptApi(payload: {
  title: string;
  content: string;
  prompt_id?: number | null;
  style_id?: number | null;
}) {
  const res = await apiClient.post("/api/libraries/scripts", payload);
  return res.data as ScriptItem;
}

export async function listAssetsApi() {
  const res = await apiClient.get("/api/assets");
  return res.data as AssetItem[];
}

export async function createAssetApi(payload: {
  title: string;
  file_type: "image" | "video" | "audio";
  file_url: string;
}) {
  const res = await apiClient.post("/api/assets", payload);
  return res.data as AssetItem;
}

export async function deleteAssetApi(assetId: number) {
  const res = await apiClient.delete(`/api/assets/${assetId}`);
  return res.data as { message: string };
}

