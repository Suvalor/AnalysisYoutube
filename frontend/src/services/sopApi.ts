import apiClient from "./apiClient";

export type SopScript = {
  id: number;
  user_id: number;
  title: string;
  outline: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type SopSegment = {
  id: number;
  script_id: number;
  segment_no: number;
  title: string;
  content: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type SopShot = {
  id: number;
  segment_id: number;
  shot_no: number;
  shot_type: string | null;
  visual_prompt: string | null;
  dialogue: string | null;
  duration_seconds: number | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type SopAsset = {
  id: number;
  shot_id: number;
  source_asset_id: number | null;
  asset_type: string;
  name: string;
  file_url: string | null;
  prompt_text: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type SopMedia = {
  id: number;
  shot_id: number;
  media_type: string;
  file_url: string | null;
  duration_seconds: number | null;
  status: string;
  created_at: string;
  updated_at: string;
};


export async function createSopScriptApi(payload: {
  title: string;
  outline?: string | null;
  status?: string;
}) {
  const res = await apiClient.post("/api/sop/scripts", payload);
  return res.data as SopScript;
}

export async function updateSopScriptApi(
  scriptId: number,
  payload: Partial<Pick<SopScript, "title" | "outline" | "status">>
) {
  const res = await apiClient.put(`/api/sop/scripts/${scriptId}`, payload);
  return res.data as SopScript;
}

export async function getSopScriptApi(scriptId: number) {
  const res = await apiClient.get(`/api/sop/scripts/${scriptId}`);
  return res.data as SopScript;
}

export async function listSopSegmentsApi(scriptId: number) {
  const res = await apiClient.get("/api/sop/segments", { params: { script_id: scriptId } });
  return res.data as SopSegment[];
}

export async function createSopSegmentApi(payload: {
  script_id: number;
  segment_no: number;
  title: string;
  content: string;
  status?: string;
}) {
  const res = await apiClient.post("/api/sop/segments", payload);
  return res.data as SopSegment;
}

export async function updateSopSegmentApi(
  segmentId: number,
  payload: Partial<Pick<SopSegment, "segment_no" | "title" | "content" | "status">>
) {
  const res = await apiClient.put(`/api/sop/segments/${segmentId}`, payload);
  return res.data as SopSegment;
}

export async function listSopShotsApi(segmentId?: number) {
  const res = await apiClient.get("/api/sop/shots", { params: segmentId ? { segment_id: segmentId } : {} });
  return res.data as SopShot[];
}

export async function createSopShotApi(payload: {
  segment_id: number;
  shot_no: number;
  shot_type?: string | null;
  visual_prompt?: string | null;
  dialogue?: string | null;
  duration_seconds?: number | null;
  status?: string;
}) {
  const res = await apiClient.post("/api/sop/shots", payload);
  return res.data as SopShot;
}

export async function updateSopShotApi(
  shotId: number,
  payload: Partial<
    Pick<SopShot, "shot_no" | "shot_type" | "visual_prompt" | "dialogue" | "duration_seconds" | "status">
  >
) {
  const res = await apiClient.put(`/api/sop/shots/${shotId}`, payload);
  return res.data as SopShot;
}

export async function listSopAssetsApi(shotId?: number) {
  const res = await apiClient.get("/api/sop/assets", { params: shotId ? { shot_id: shotId } : {} });
  return res.data as SopAsset[];
}

export async function createSopAssetApi(payload: {
  shot_id: number;
  source_asset_id?: number | null;
  asset_type?: string;
  name: string;
  file_url?: string | null;
  prompt_text?: string | null;
  status?: string;
}) {
  const res = await apiClient.post("/api/sop/assets", payload);
  return res.data as SopAsset;
}

export async function listSopMediaApi(shotId?: number) {
  const res = await apiClient.get("/api/sop/media", { params: shotId ? { shot_id: shotId } : {} });
  return res.data as SopMedia[];
}

export async function streamSopAiSplitApi(
  payload: { outline_markdown: string; model?: string },
  onEvent: (event: any) => void,
  signal?: AbortSignal
) {
  const baseURL = (apiClient.defaults.baseURL || "http://localhost:8000").replace(/\/$/, "");
  const token = localStorage.getItem("access_token") || "";
  const resp = await fetch(`${baseURL}/api/sop/segments/ai-split`, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify(payload),
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`流式连接失败: ${resp.status}`);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";
    for (const frame of frames) {
      const line = frame
        .split("\n")
        .find((x) => x.startsWith("data: "));
      if (!line) continue;
      const raw = line.replace(/^data:\s*/, "");
      try {
        onEvent(JSON.parse(raw));
      } catch {
        // ignore malformed chunk
      }
    }
  }
}

export async function createShotsFromSegmentsApi(payload: { script_id: number; replace_existing?: boolean }) {
  const res = await apiClient.post("/api/sop/shots/from-segments", payload);
  return res.data as SopShot[];
}
