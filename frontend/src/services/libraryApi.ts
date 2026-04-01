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

export type JimengTaskSubmitResponse = {
  task_id: string;
  raw: any;
};

export type JimengTaskStatusResponse = {
  task_id: string;
  status: string;
  result?: any;
  raw: any;
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

export async function uploadAssetWithProcessApi(payload: {
  file: File;
  remove_watermark: boolean;
}) {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("remove_watermark", String(payload.remove_watermark));
  const res = await apiClient.post("/api/assets/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  });
  return res.data as {
    id?: number;
    title?: string;
    file_type?: "image" | "video" | "audio";
    file_url?: string;
    created_at?: string;
  };
}

export async function jimengGenerateApi(payload: {
  model_name: string;
  prompt: string;
  negative_prompt?: string;
  width?: number;
  height?: number;
  ratio?: string;
  extra?: Record<string, any>;
}) {
  const res = await apiClient.post("/api/v1/jimeng/generate", payload);
  return res.data as JimengTaskSubmitResponse;
}

export async function jimengTaskStatusApi(taskId: string) {
  const res = await apiClient.get(`/api/v1/jimeng/status/${taskId}`);
  return res.data as JimengTaskStatusResponse;
}


