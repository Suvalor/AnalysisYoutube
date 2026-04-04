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

export type ModelItem = {
  id: number;
  user_id: number;
  name: string;
  api_base_url: string;
  supported_models_json: string | null;
  has_api_key: boolean;
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
  /** AI_WORKSHOP | MANUAL；旧数据缺省时前端按 AI_WORKSHOP 处理 */
  origin_type?: string;
  /** 知识库置顶 */
  is_pinned?: boolean;
  created_at: string;
  updated_at: string;
};

export type AssetItem = {
  id: number;
  user_id: number;
  title: string;
  file_type: "image" | "video" | "audio";
  file_url: string;
  /** 私有桶列表/预览应优先使用（后端签名 + 自定义域名） */
  access_url: string;
  source?: string;
  storage_platform?: string;
  storage_object_key?: string | null;
  file_size?: number | null;
  created_at: string;
  updated_at: string;
};

export type AssetListParams = {
  page?: number;
  page_size?: number;
  file_type?: "image" | "video" | "audio";
  /** YYYY-MM-DD */
  date_start?: string;
  date_end?: string;
  q?: string;
  sort_by?: "created_at" | "file_size";
  sort_order?: "asc" | "desc";
};

export type AssetListResult = {
  items: AssetItem[];
  total: number;
  page: number;
  page_size: number;
  sort_by: "created_at" | "file_size";
  sort_order: "asc" | "desc";
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

export async function createPromptApi(payload: { title: string; content: string }) {
  const res = await apiClient.post("/api/libraries/prompts", payload);
  return res.data as PromptItem;
}

export async function updatePromptApi(promptId: number, payload: { title?: string; content?: string }) {
  const res = await apiClient.put(`/api/libraries/prompts/${promptId}`, payload);
  return res.data as PromptItem;
}

export async function getPromptApi(promptId: number) {
  const res = await apiClient.get(`/api/libraries/prompts/${promptId}`);
  return res.data as PromptItem;
}

export async function deletePromptApi(promptId: number) {
  const res = await apiClient.delete(`/api/libraries/prompts/${promptId}`);
  return res.data as { message: string };
}

export async function listStylesApi() {
  const res = await apiClient.get("/api/libraries/styles");
  return res.data as StyleItem[];
}

export async function createStyleApi(payload: { title: string; content: string }) {
  const res = await apiClient.post("/api/libraries/styles", payload);
  return res.data as StyleItem;
}

export async function updateStyleApi(styleId: number, payload: { title?: string; content?: string }) {
  const res = await apiClient.put(`/api/libraries/styles/${styleId}`, payload);
  return res.data as StyleItem;
}

export async function deleteStyleApi(styleId: number) {
  const res = await apiClient.delete(`/api/libraries/styles/${styleId}`);
  return res.data as { message: string };
}

export async function listModelsApi() {
  const res = await apiClient.get("/api/libraries/models");
  return res.data as ModelItem[];
}

export async function createModelApi(payload: {
  name: string;
  api_base_url: string;
  api_key?: string;
  supported_models_json?: string | null;
}) {
  const res = await apiClient.post("/api/libraries/models", payload);
  return res.data as ModelItem;
}

export async function updateModelApi(
  modelId: number,
  payload: {
    name?: string;
    api_base_url?: string;
    api_key?: string;
    supported_models_json?: string | null;
  }
) {
  const res = await apiClient.put(`/api/libraries/models/${modelId}`, payload);
  return res.data as ModelItem;
}

export async function deleteModelApi(modelId: number) {
  const res = await apiClient.delete(`/api/libraries/models/${modelId}`);
  return res.data as { message: string };
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

/** 知识库手动新建（与 AI 脚本工坊 createScriptApi 分离） */
export async function createManualKnowledgeScriptApi(payload: { title: string; plot: string }) {
  const res = await apiClient.post("/api/knowledge-base/manual-create", payload);
  return res.data as ScriptItem;
}

export type ListScriptsParams = {
  includeDeleted?: boolean;
  sort_by?: "updated_at" | "created_at";
};

/** 支持布尔简写（仅回收站）或完整参数 */
export async function listScriptsApi(params: boolean | ListScriptsParams = false) {
  const opts: ListScriptsParams = typeof params === "boolean" ? { includeDeleted: params } : params ?? {};
  const include_deleted = opts.includeDeleted ?? false;
  const sort_by = opts.sort_by ?? "updated_at";
  const res = await apiClient.get("/api/libraries/scripts", {
    params: { include_deleted, sort_by },
  });
  return res.data as ScriptItem[];
}

/** 知识库置顶切换 */
export async function pinKnowledgeScriptApi(id: number, isPinned: boolean) {
  const res = await apiClient.post("/api/knowledge/pin", { id, is_pinned: isPinned });
  return res.data as ScriptItem;
}

export async function getScriptApi(scriptId: number) {
  const res = await apiClient.get(`/api/libraries/scripts/${scriptId}`);
  return res.data as ScriptItem;
}

export async function deleteScriptApi(scriptId: number) {
  const res = await apiClient.delete(`/api/libraries/scripts/${scriptId}`);
  return res.data as { message: string };
}

export async function restoreScriptApi(scriptId: number) {
  const res = await apiClient.post(`/api/libraries/scripts/${scriptId}/restore`);
  return res.data as ScriptItem;
}

export async function listAssetsApi(params?: AssetListParams) {
  const res = await apiClient.get("/api/assets", { params });
  return res.data as AssetListResult;
}

export async function createAssetApi(payload: {
  title: string;
  file_type: "image" | "video" | "audio";
  file_url: string;
  file_size?: number | null;
  source?: string;
  storage_platform?: string;
  storage_object_key?: string | null;
}) {
  const res = await apiClient.post("/api/assets", payload);
  return res.data as AssetItem;
}

/** 申请浏览器 PUT 直传预签名（不走 Node SDK） */
export type AssetPresignUploadBody = {
  filename: string;
  content_type?: string | null;
  module?: "MANUAL" | "SOP" | "INSPIRATION";
};

export type AssetPresignUploadResult = {
  upload_url: string;
  final_access_url: string;
  storage_platform: string;
  storage_object_key: string;
  file_type: "image" | "video" | "audio";
  expires_in: number;
  method: "PUT";
  required_headers: Record<string, string>;
};

export async function getAssetUploadParamsApi(body: AssetPresignUploadBody, expires = 600) {
  const res = await apiClient.post("/api/assets/get_upload_params", body, {
    params: { expires },
  });
  return res.data as AssetPresignUploadResult;
}

/**
 * 使用原生 fetch PUT 上传至云厂商预签名 URL（避免 axios 走 Node 适配器链）。
 * required_headers 须与签发预签名时一致（尤其 Content-Type）。
 */
export async function putFileToPresignedUrl(
  uploadUrl: string,
  file: File,
  requiredHeaders: Record<string, string>
): Promise<void> {
  const headers = new Headers();
  for (const [k, v] of Object.entries(requiredHeaders || {})) {
    if (v) headers.set(k, v);
  }
  const res = await fetch(uploadUrl, { method: "PUT", body: file, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`对象存储直传失败（HTTP ${res.status}）${text ? `：${text.slice(0, 240)}` : ""}`);
  }
}

export async function deleteAssetApi(assetId: number) {
  const res = await apiClient.delete(`/api/assets/${assetId}`);
  return res.data as { message: string };
}

/** 素材库单条访问地址（私有桶为 presigned，Host 已按组织配置替换自定义域名） */
export async function getAssetAccessUrlApi(assetId: number, expires = 3600) {
  const res = await apiClient.get(`/api/assets/${assetId}/access-url`, {
    params: { expires },
  });
  return res.data as { url: string; mode: "presigned" | "public_fallback"; expires_in: number | null };
}

/** 与素材库相同的上传链路：OSS 持久化，返回可公开访问的 file_url */
export type MaterialUploadResult = {
  id: number;
  title: string;
  file_type: "image" | "video";
  file_url: string;
  access_url?: string;
  source?: string;
  storage_platform?: string;
  storage_object_key?: string | null;
  file_size?: number | null;
  created_at: string;
  remove_watermark?: boolean;
  /** 后端返回：未启用去水印 / 去水印已完成 / 跳过原因等 */
  process_info?: string;
};

/** 按素材记录的存储平台生成访问 URL（签名或公开回退），不依赖前端全局开关 */
export async function getMaterialAccessUrlApi(materialId: number, expires = 3600) {
  const res = await apiClient.get(`/api/v1/materials/${materialId}/access-url`, {
    params: { expires },
  });
  return res.data as { url: string; mode: "presigned" | "public_fallback"; expires_in: number | null };
}

export async function uploadMaterialImageApi(file: File, removeWatermark = false) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("remove_watermark", String(removeWatermark));
  formData.append("source", "INSPIRATION");
  const res = await apiClient.post("/api/v1/materials/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  });
  return res.data as MaterialUploadResult;
}

export type AssetUploadResult = {
  id: number;
  title: string;
  file_type: "image" | "video" | "audio";
  file_url: string;
  access_url?: string;
  source?: string;
  storage_platform?: string;
  storage_object_key?: string | null;
  file_size?: number | null;
  created_at: string;
  remove_watermark?: boolean;
  /** 后端返回：未启用去水印 / 去水印已完成 / 跳过原因等 */
  process_info?: string;
};

export async function uploadAssetWithProcessApi(payload: {
  file: File;
  remove_watermark: boolean;
  /** 素材库页勿传；SOP 内上传传 SOP */
  source?: "MANUAL" | "SOP" | "INSPIRATION";
}): Promise<AssetUploadResult> {
  const source = payload.source ?? "MANUAL";
  const file = payload.file;

  if (payload.remove_watermark) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("remove_watermark", "true");
    formData.append("source", source);
    const res = await apiClient.post("/api/assets/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    });
    return res.data as AssetUploadResult;
  }

  const ct = file.type?.trim() || "application/octet-stream";
  const presign = await getAssetUploadParamsApi(
    { filename: file.name, content_type: ct, module: source },
    600
  );
  await putFileToPresignedUrl(presign.upload_url, file, presign.required_headers);

  const row = await createAssetApi({
    title: file.name,
    file_type: presign.file_type,
    file_url: presign.final_access_url,
    file_size: file.size,
    source,
    storage_platform: presign.storage_platform,
    storage_object_key: presign.storage_object_key,
  });

  return {
    id: row.id,
    title: row.title,
    file_type: row.file_type,
    file_url: row.file_url,
    access_url: row.access_url,
    source: row.source,
    storage_platform: row.storage_platform,
    storage_object_key: row.storage_object_key ?? null,
    file_size: row.file_size ?? file.size,
    created_at: row.created_at,
    remove_watermark: false,
    process_info: "未启用去水印",
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


