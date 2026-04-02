import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Button, Card, Drawer, Input, Modal, Select, Spin, Steps, Table, Typography, Upload, message } from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getScriptApi, listPromptsApi, type PromptItem } from "@/services/libraryApi";
import { uploadAssetWithProcessApi } from "@/services/libraryApi";
import { getScriptModelsApi, type ScriptModelOption } from "@/services/scriptsApi";
import {
  createShotsFromSegmentsApi,
  createSopAssetApi,
  createSopScriptApi,
  createSopSegmentApi,
  getSopScriptApi,
  listSopAssetsApi,
  listSopSegmentsApi,
  listSopShotsApi,
  listSopMediaApi,
  streamSopAiSplitApi,
  updateSopSegmentApi,
  updateSopScriptApi,
  updateSopShotApi,
  type SopAsset,
  type SopMedia,
  type SopSegment,
  type SopShot,
} from "@/services/sopApi";
import MarkdownEditorToggle from "@/components/MarkdownEditorToggle";
import {
  completeYouTubeOAuthApi,
  getYouTubeOAuthStatusApi,
  getYouTubeOAuthUrlApi,
  publishYouTubeApi,
  type YouTubeOAuthStatusResponse,
} from "@/services/youtubeApi";
import { linkInspirationPlotApi } from "@/services/inspirationApi";

const { Text, Title } = Typography;
const { TextArea } = Input;

/** 私有桶下优先使用后端签名的 access_url 做展示与可下载链接 */
function sopFileDisplayUrl(row: { access_url?: string | null; file_url?: string | null }): string {
  return (row.access_url || row.file_url || "").trim();
}

type SourceScript = {
  id: number;
  title: string;
  content: string;
};

export default function ScriptWorkflowSOP() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const inspirationIdParam = searchParams.get("inspirationId");
  const inspirationLinkId = useMemo(() => {
    if (!inspirationIdParam) return null;
    const n = Number(inspirationIdParam);
    return Number.isFinite(n) && n > 0 ? n : null;
  }, [inspirationIdParam]);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [splitting, setSplitting] = useState(false);
  const [sourceScript, setSourceScript] = useState<SourceScript | null>(null);
  const [outlineMarkdown, setOutlineMarkdown] = useState("");
  const [aiSegmentsMarkdown, setAiSegmentsMarkdown] = useState("");
  const [sopScriptId, setSopScriptId] = useState<number | null>(null);
  const [segments, setSegments] = useState<SopSegment[]>([]);
  const [shots, setShots] = useState<SopShot[]>([]);
  const [assets, setAssets] = useState<SopAsset[]>([]);
  const [generatingShots, setGeneratingShots] = useState(false);
  const [selectedSegmentId, setSelectedSegmentId] = useState<number | null>(null);
  const [savingShotIds, setSavingShotIds] = useState<Record<number, boolean>>({});
  const [assetDrawerOpen, setAssetDrawerOpen] = useState(false);
  const [publicAssets, setPublicAssets] = useState<SopAsset[]>([]);
  const [activeDragAsset, setActiveDragAsset] = useState<SopAsset | null>(null);
  const [mediaRows, setMediaRows] = useState<SopMedia[]>([]);
  const [oauthStatus, setOauthStatus] = useState<YouTubeOAuthStatusResponse | null>(null);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishModalOpen, setPublishModalOpen] = useState(false);
  const [publishMediaId, setPublishMediaId] = useState<number | null>(null);
  const [publishTitle, setPublishTitle] = useState("");
  const [publishDescription, setPublishDescription] = useState("");
  const [publishPrivacy, setPublishPrivacy] = useState<"private" | "public" | "unlisted">("private");
  const [savingOutline, setSavingOutline] = useState(false);
  const [savingSegments, setSavingSegments] = useState(false);
  const [modelOptions, setModelOptions] = useState<ScriptModelOption[]>([]);
  const [agentOptions, setAgentOptions] = useState<PromptItem[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const shotSaveTimersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());
  const latestShotsRef = useRef<SopShot[]>([]);
  const currentSplitTaskRef = useRef<string | null>(null);
  const splitTextRef = useRef("");
  const splitAbortRef = useRef<AbortController | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  useEffect(() => {
    let mounted = true;
    (async () => {
      const rawId = localStorage.getItem("sop_current_script_id");
      if (!rawId) {
        message.warning("未选择剧本，请先从知识库进入");
        setLoading(false);
        return;
      }
      try {
        const data = await getScriptApi(Number(rawId));
        if (!mounted) return;
        setSourceScript({ id: data.id, title: data.title, content: data.content });
        setOutlineMarkdown(data.content || "");
        const savedSopId = Number(localStorage.getItem(`sop_current_sop_script_id_${rawId}`) || "");
        if (!Number.isNaN(savedSopId) && savedSopId > 0) setSopScriptId(savedSopId);
      } catch (e: any) {
        if (!mounted) return;
        message.error(e?.response?.data?.detail ?? e?.message ?? "加载剧本失败");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [models, agents] = await Promise.all([getScriptModelsApi(), listPromptsApi()]);
        if (!mounted) return;
        setModelOptions(models);
        setAgentOptions(agents);
        if (models.length > 0) setSelectedModelId((prev) => prev ?? models[0].value);
        if (agents.length > 0) setSelectedAgentId((prev) => prev ?? agents[0].id);
      } catch (e: any) {
        if (!mounted) return;
        message.warning(e?.response?.data?.detail ?? e?.message ?? "加载模型/智能体配置失败");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const steps = useMemo(
    () => [
      { title: "剧本设定" },
      { title: "剧情拆解" },
      { title: "分镜与资产创作" },
      { title: "合成与发布" },
    ],
    []
  );

  const ensureSopScript = async () => {
    if (!sourceScript) throw new Error("缺少剧本数据");
    if (sopScriptId) return sopScriptId;
    const created = await createSopScriptApi({
      title: sourceScript.title,
      outline: outlineMarkdown,
      status: "draft",
    });
    setSopScriptId(created.id);
    localStorage.setItem(`sop_current_sop_script_id_${sourceScript.id}`, String(created.id));
    return created.id;
  };

  useEffect(() => {
    latestShotsRef.current = shots;
  }, [shots]);

  useEffect(() => {
    return () => {
      shotSaveTimersRef.current.forEach((t) => clearTimeout(t));
      shotSaveTimersRef.current.clear();
      splitAbortRef.current?.abort();
    };
  }, []);

  const persistOutline = async () => {
    if (!outlineMarkdown.trim()) {
      message.warning("剧本大纲为空，无法保存");
      return;
    }
    setSavingOutline(true);
    try {
      const sid = await ensureSopScript();
      await updateSopScriptApi(sid, { outline: outlineMarkdown });
      setSourceScript((prev) => (prev ? { ...prev, content: outlineMarkdown } : prev));
      message.success("剧本大纲已保存");
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "保存大纲失败");
    } finally {
      setSavingOutline(false);
    }
  };

  const handleAiSplitSegments = async () => {
    if (!outlineMarkdown.trim()) {
      message.warning("剧本大纲为空，无法拆解");
      return;
    }
    setSplitting(true);
    try {
      await persistOutline();
      const reqId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      currentSplitTaskRef.current = reqId;
      splitTextRef.current = "";
      setAiSegmentsMarkdown("");
      const maxRetries = 3;
      let attempt = 0;
      while (attempt < maxRetries) {
        try {
          splitAbortRef.current?.abort();
          splitAbortRef.current = new AbortController();
          await streamSopAiSplitApi(
            {
              outline_markdown: outlineMarkdown,
              model_id: selectedModelId ?? undefined,
              agent_id: selectedAgentId ?? undefined,
            },
            (event) => {
              if (currentSplitTaskRef.current !== reqId) return;
              const t = String(event?.type || "");
              if (t === "snapshot") {
                splitTextRef.current = String(event.content || "");
                setAiSegmentsMarkdown(splitTextRef.current);
                return;
              }
              if (t === "delta") {
                splitTextRef.current += String(event.text || event.content || "");
                setAiSegmentsMarkdown(splitTextRef.current);
                return;
              }
              if (t === "done") return;
              if (t === "error") {
                throw new Error(String(event.message || "AI 拆解失败"));
              }
            },
            splitAbortRef.current.signal
          );
          break;
        } catch (err) {
          attempt += 1;
          if (attempt >= maxRetries) throw err;
          message.warning(`流式连接中断，正在重试（${attempt}/${maxRetries - 1}）`);
          await new Promise((r) => setTimeout(r, 1000 * attempt));
        }
      }
      setStep(1);
      message.success("AI 拆解完成，可继续人工调整");
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "AI 拆解失败");
    } finally {
      setSplitting(false);
    }
  };

  const parseSegmentsFromMarkdown = (raw: string): Array<{ title: string; content: string }> => {
    const text = raw.trim();
    if (!text) return [];
    const blocks = text
      .split(/\n(?=##\s+)/g)
      .map((x) => x.trim())
      .filter(Boolean);
    if (blocks.length === 0) return [];
    return blocks.map((block, idx) => {
      const lines = block.split("\n");
      const head = (lines[0] || "").replace(/^##\s*/, "").trim();
      const title = head || `片段 ${idx + 1}`;
      const content = lines.slice(1).join("\n").trim() || head;
      return { title, content };
    });
  };

  const handleSaveSegmentsFromMarkdown = async () => {
    const parsed = parseSegmentsFromMarkdown(aiSegmentsMarkdown);
    if (parsed.length === 0) {
      message.warning("没有可保存的片段内容，请先执行 AI 拆解或手动补充");
      return;
    }
    setSavingSegments(true);
    try {
      const sid = await ensureSopScript();
      const existing = (await listSopSegmentsApi(sid)).sort((a, b) => a.segment_no - b.segment_no);
      for (let i = 0; i < parsed.length; i += 1) {
        const seg = parsed[i]!;
        const current = existing[i];
        if (current) {
          await updateSopSegmentApi(current.id, {
            segment_no: i + 1,
            title: seg.title,
            content: seg.content,
            status: "draft",
          });
        } else {
          await createSopSegmentApi({
            script_id: sid,
            segment_no: i + 1,
            title: seg.title,
            content: seg.content,
            status: "draft",
          });
        }
      }
      const latest = await listSopSegmentsApi(sid);
      const sorted = latest.sort((a, b) => a.segment_no - b.segment_no);
      setSegments(sorted);
      setSelectedSegmentId((prev) => prev ?? sorted[0]?.id ?? null);
      const hydrated = sorted
        .map((s) => `## 片段 ${s.segment_no}：${s.title}\n${s.content}`)
        .join("\n\n");
      setAiSegmentsMarkdown(hydrated);
      message.success("片段已保存到 segments");
      if (inspirationLinkId) {
        try {
          await linkInspirationPlotApi(inspirationLinkId, { plot_id: sid });
          message.success("灵感中心已标记为「已生成剧情」并关联剧情 ID");
        } catch (e: unknown) {
          const msg =
            e && typeof e === "object" && "response" in e
              ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
              : undefined;
          message.warning(
            typeof msg === "string" ? msg : "关联灵感中心失败，可在灵感中心查看或重试保存片段"
          );
        }
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "保存片段失败");
    } finally {
      setSavingSegments(false);
    }
  };

  useEffect(() => {
    if (!selectedSegmentId) {
      setShots([]);
      setAssets([]);
      return;
    }
    let mounted = true;
    (async () => {
      try {
        const segShots = await listSopShotsApi(selectedSegmentId);
        if (!mounted) return;
        const sortedShots = segShots.sort((a, b) => a.shot_no - b.shot_no);
        setShots(sortedShots);
        const allAssets: SopAsset[] = [];
        for (const shot of sortedShots) {
          const shotAssets = await listSopAssetsApi(shot.id);
          allAssets.push(...shotAssets);
        }
        if (!mounted) return;
        setAssets(allAssets);
      } catch (e: any) {
        if (!mounted) return;
        message.error(e?.response?.data?.detail ?? e?.message ?? "加载分镜/资产失败");
      }
    })();
    return () => {
      mounted = false;
    };
  }, [selectedSegmentId]);

  const handleShotFieldChange = (shotId: number, patch: Partial<SopShot>) => {
    setShots((prev) => prev.map((s) => (s.id === shotId ? { ...s, ...patch } : s)));
  };

  const saveShotNow = async (shot: SopShot) => {
    setSavingShotIds((prev) => ({ ...prev, [shot.id]: true }));
    try {
      const updated = await updateSopShotApi(shot.id, {
        visual_prompt: shot.visual_prompt,
      });
      setShots((prev) => prev.map((s) => (s.id === shot.id ? updated : s)));
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "分镜保存失败");
    } finally {
      setSavingShotIds((prev) => ({ ...prev, [shot.id]: false }));
    }
  };

  const queueShotAutoSave = (shotId: number) => {
    const old = shotSaveTimersRef.current.get(shotId);
    if (old) clearTimeout(old);
    const timer = setTimeout(() => {
      const row = latestShotsRef.current.find((x) => x.id === shotId);
      if (row) void saveShotNow(row);
      shotSaveTimersRef.current.delete(shotId);
    }, 700);
    shotSaveTimersRef.current.set(shotId, timer);
  };

  useEffect(() => {
    if (!sopScriptId) return;
    let mounted = true;
    (async () => {
      try {
        const row = await getSopScriptApi(sopScriptId);
        if (!mounted) return;
        if (sourceScript && row.title !== sourceScript.title) {
          setSopScriptId(null);
          if (sourceScript.id) localStorage.removeItem(`sop_current_sop_script_id_${sourceScript.id}`);
          return;
        }
        const latest = await listSopSegmentsApi(sopScriptId);
        if (!mounted) return;
        const sorted = latest.sort((a, b) => a.segment_no - b.segment_no);
        setSegments(sorted);
        setSelectedSegmentId((prev) => prev ?? sorted[0]?.id ?? null);
        const hydrated = sorted
          .map((s) => `## 片段 ${s.segment_no}：${s.title}\n${s.content}`)
          .join("\n\n");
        if (hydrated.trim()) setAiSegmentsMarkdown(hydrated);
      } catch {
        if (!mounted) return;
        setSopScriptId(null);
        if (sourceScript?.id) localStorage.removeItem(`sop_current_sop_script_id_${sourceScript.id}`);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [sopScriptId, sourceScript]);

  const handleUploadToShot = async (shotId: number, file: File) => {
    try {
      const uploadRes = await uploadAssetWithProcessApi({
        file,
        remove_watermark: false,
        source: "SOP",
      });
      const created = await createSopAssetApi({
        shot_id: shotId,
        name: uploadRes.title || file.name,
        asset_type: uploadRes.file_type || "image",
        file_url: uploadRes.file_url || null,
        storage_platform: uploadRes.storage_platform ?? undefined,
        storage_object_key: uploadRes.storage_object_key ?? undefined,
        status: "draft",
      });
      setAssets((prev) => [...prev, created]);
      message.success("素材上传并绑定成功");
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "素材上传失败");
    }
  };

  const reloadPublicAssets = async () => {
    const rows = await listSopAssetsApi();
    setPublicAssets(rows);
  };

  const generateShotsFromSegments = async () => {
    if (!sopScriptId || segments.length === 0) {
      message.warning("请先完成剧情拆解再生成分镜");
      return;
    }
    setGeneratingShots(true);
    try {
      await createShotsFromSegmentsApi({ script_id: sopScriptId, replace_existing: true });
      const allShots: SopShot[] = [];
      for (const seg of segments) {
        const segShots = await listSopShotsApi(seg.id);
        allShots.push(...segShots);
      }
      setShots(allShots.sort((a, b) => a.segment_id - b.segment_id || a.shot_no - b.shot_no));
      setStep((prev) => Math.max(prev, 2));
      message.success("分镜草案已生成");
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "生成分镜失败");
    } finally {
      setGeneratingShots(false);
    }
  };

  const assetByShot = useMemo(() => {
    const m = new Map<number, SopAsset[]>();
    for (const a of assets) {
      const arr = m.get(a.shot_id) ?? [];
      arr.push(a);
      m.set(a.shot_id, arr);
    }
    return m;
  }, [assets]);

  const onDragStart = (event: DragStartEvent) => {
    const id = String(event.active.id);
    if (!id.startsWith("public-asset-")) return;
    const aid = Number(id.replace("public-asset-", ""));
    setActiveDragAsset(publicAssets.find((x) => x.id === aid) ?? null);
  };

  const onDragEnd = async (event: DragEndEvent) => {
    setActiveDragAsset(null);
    const activeId = String(event.active.id);
    const overId = event.over ? String(event.over.id) : "";
    if (!activeId.startsWith("public-asset-") || !overId.startsWith("shot-drop-")) return;

    const assetId = Number(activeId.replace("public-asset-", ""));
    const shotId = Number(overId.replace("shot-drop-", ""));
    if (Number.isNaN(assetId) || Number.isNaN(shotId)) return;
    const source = publicAssets.find((x) => x.id === assetId);
    if (!source) return;

    try {
      await createSopAssetApi({
        shot_id: shotId,
        source_asset_id: source.id,
        name: source.name,
        asset_type: source.asset_type,
        file_url: source.file_url,
        prompt_text: source.prompt_text,
        status: "draft",
      });
      const latestForShot = await listSopAssetsApi(shotId);
      setAssets((prev) => [...prev.filter((x) => x.shot_id !== shotId), ...latestForShot]);
      message.success("拖拽绑定成功");
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "拖拽绑定失败");
    }
  };

  const loadMediaByShots = async (targetShots: SopShot[]) => {
    const all: SopMedia[] = [];
    for (const shot of targetShots) {
      const rows = await listSopMediaApi(shot.id);
      all.push(...rows);
    }
    setMediaRows(all);
  };

  useEffect(() => {
    void loadMediaByShots(shots);
  }, [shots]);

  const loadOAuthStatus = async () => {
    try {
      const s = await getYouTubeOAuthStatusApi();
      setOauthStatus(s);
    } catch {
      setOauthStatus({ connected: false, channel_id: null, expires_at: null });
    }
  };

  useEffect(() => {
    void loadOAuthStatus();
  }, []);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) return;
    const state = searchParams.get("state");
    let mounted = true;
    (async () => {
      setOauthLoading(true);
      try {
        await completeYouTubeOAuthApi({
          code,
          state,
          redirect_uri: `${window.location.origin}/sop-workflow`,
        });
        if (mounted) {
          await loadOAuthStatus();
          message.success("YouTube 授权成功");
          navigate("/sop-workflow", { replace: true });
        }
      } catch (e: any) {
        if (mounted) message.error(e?.response?.data?.detail ?? e?.message ?? "OAuth 回调处理失败");
      } finally {
        if (mounted) setOauthLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [navigate, searchParams]);

  const allMediaDone = useMemo(
    () =>
      mediaRows.length > 0 &&
      mediaRows.every((x) => ["success", "completed", "done", "ready"].includes(String(x.status).toLowerCase())),
    [mediaRows]
  );

  const handleConnectYouTube = async () => {
    try {
      setOauthLoading(true);
      const data = await getYouTubeOAuthUrlApi();
      window.location.href = data.auth_url;
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "获取授权地址失败");
    } finally {
      setOauthLoading(false);
    }
  };

  const handlePublishYouTube = async () => {
    const targetMedia = mediaRows.find((x) => x.id === publishMediaId) ?? null;
    const publishUrl = targetMedia ? sopFileDisplayUrl(targetMedia) : "";
    if (!publishUrl) {
      message.warning("暂无可发布视频");
      return;
    }
    if (!publishTitle.trim()) {
      message.warning("缺少剧本标题");
      return;
    }
    setPublishing(true);
    try {
      const res = await publishYouTubeApi({
        media_url: publishUrl,
        title: publishTitle.trim(),
        description: publishDescription.trim().slice(0, 5000),
        privacy_status: publishPrivacy,
      });
      message.success(res.message || "发布请求已提交");
      setPublishModalOpen(false);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? e?.message ?? "发布失败");
    } finally {
      setPublishing(false);
    }
  };

  const openPublishModal = () => {
    const firstMedia = mediaRows.find((x) => sopFileDisplayUrl(x));
    setPublishMediaId(firstMedia?.id ?? null);
    setPublishTitle(sourceScript?.title || "");
    setPublishDescription((sourceScript?.content || "").slice(0, 5000));
    setPublishPrivacy("private");
    setPublishModalOpen(true);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-white">
        <Spin />
      </div>
    );
  }

  return (
    <div className="h-full bg-white p-4 md:p-6">
      <div className="max-w-[1400px] mx-auto space-y-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <Steps current={step} items={steps} />
        </div>

        <Card className="!border-slate-200 !shadow-none">
          <Title level={4} className="!mb-3">
            步骤 1：剧本设定
          </Title>
          <div className="mb-2 text-slate-700">
            <Text strong>标题：</Text>
            {sourceScript?.title ?? "-"}
          </div>
          <MarkdownEditorToggle
            value={outlineMarkdown}
            onChange={setOutlineMarkdown}
            onBlur={() => void persistOutline()}
            minRows={10}
            placeholder="请输入剧本大纲（Markdown）"
          />
          <div className="mt-3">
            <Button type="default" onClick={persistOutline} loading={savingOutline}>
              保存大纲
            </Button>
          </div>
        </Card>

        <Card className="!border-slate-200 !shadow-none">
          <Title level={4} className="!mb-3">
            步骤 2：剧情拆解
          </Title>
          <div className="mb-3 flex gap-2">
            <Select
              size="middle"
              placeholder="选择模型"
              value={selectedModelId ?? undefined}
              onChange={(v) => setSelectedModelId(v)}
              options={modelOptions.map((m) => ({ value: m.value, label: m.label }))}
              className="w-48"
            />
            <Select
              size="middle"
              placeholder="选择智能体/提示词"
              value={selectedAgentId ?? undefined}
              onChange={(v) => setSelectedAgentId(v)}
              options={agentOptions.map((a) => ({ value: a.id, label: a.title }))}
              className="w-56"
            />
            <Button type="primary" onClick={handleAiSplitSegments} loading={splitting}>
              AI 智能拆解分镜
            </Button>
            <Button onClick={handleSaveSegmentsFromMarkdown} loading={savingSegments}>
              保存片段
            </Button>
          </div>
          <MarkdownEditorToggle
            value={aiSegmentsMarkdown}
            onChange={setAiSegmentsMarkdown}
            minRows={12}
            placeholder="点击“AI 智能拆解分镜”后，将在这里展示可编辑的 Markdown 结果"
          />
          {segments.length > 0 && (
            <div className="mt-2 text-xs text-slate-500">
              已保存片段数：{segments.length}（可继续在上方 Markdown 中人工调优后再次保存）
            </div>
          )}
        </Card>

        <Card className="!border-slate-200 !shadow-none">
          <Title level={4} className="!mb-2">
            步骤 3：分镜与资产创作
          </Title>
          <div className="mb-3 flex flex-col md:flex-row gap-2 md:items-center">
            <Button loading={generatingShots} onClick={generateShotsFromSegments} type="primary">
              生成分镜草案
            </Button>
            <Select
              placeholder="选择片段"
              value={selectedSegmentId ?? undefined}
              onChange={(v) => setSelectedSegmentId(v)}
              options={segments.map((s) => ({ value: s.id, label: `片段 ${s.segment_no}：${s.title}` }))}
              className="md:w-[420px]"
            />
            <Button
              onClick={async () => {
                await reloadPublicAssets();
                setAssetDrawerOpen(true);
              }}
            >
              打开公共资产库
            </Button>
          </div>
          <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd} onDragCancel={() => setActiveDragAsset(null)}>
            <div className="space-y-3">
              {shots.map((shot) => (
                <ShotEditableCard
                  key={shot.id}
                  shot={shot}
                  assets={assetByShot.get(shot.id) ?? []}
                  saving={Boolean(savingShotIds[shot.id])}
                  onChange={(shotId, patch) => {
                    handleShotFieldChange(shotId, patch);
                    queueShotAutoSave(shotId);
                  }}
                  onUpload={handleUploadToShot}
                />
              ))}
              {shots.length === 0 && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-slate-500">
                  当前片段暂无分镜，请先点击“生成分镜草案”。
                </div>
              )}
            </div>
            <Drawer title="公共资产库" open={assetDrawerOpen} onClose={() => setAssetDrawerOpen(false)} width={360}>
              <div className="space-y-2">
                {publicAssets.map((asset) => (
                  <DraggablePublicAsset key={asset.id} asset={asset} />
                ))}
                {publicAssets.length === 0 && (
                  <div className="text-xs text-slate-500 border border-dashed border-slate-300 rounded p-3 text-center">暂无公共资产</div>
                )}
              </div>
              <div className="mt-3 text-xs text-slate-500">拖拽右侧资产到左侧卡片“资产与媒体”区域，即可复制并关联到目标分镜。</div>
            </Drawer>
            <DragOverlay>
              {activeDragAsset ? (
                <div className="w-56 rounded-lg border border-blue-300 bg-white p-2 shadow-sm">
                  <div className="text-sm font-medium text-slate-800 truncate">{activeDragAsset.name}</div>
                  <div className="text-xs text-slate-500">拖拽中...</div>
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        </Card>

        <Card className="!border-slate-200 !shadow-none">
          <Title level={4} className="!mb-2">
            步骤 4：合成与发布
          </Title>
          <div className="space-y-3">
            <div className="flex flex-col md:flex-row gap-2 md:items-center md:justify-between">
              <div className="text-sm text-slate-600">
                OAuth 状态：{oauthStatus?.connected ? `已连接（频道 ${oauthStatus.channel_id || "-"})` : "未连接"}
              </div>
              <div className="flex gap-2">
                <Button onClick={handleConnectYouTube} loading={oauthLoading}>
                  连接 YouTube
                </Button>
                <Button
                  type="primary"
                  disabled={!allMediaDone || !oauthStatus?.connected}
                  loading={publishing}
                  onClick={openPublishModal}
                >
                  发布到 YouTube
                </Button>
              </div>
            </div>
            <Table<SopMedia>
              rowKey="id"
              size="small"
              pagination={{ pageSize: 6 }}
              dataSource={mediaRows}
              columns={[
                { title: "媒体ID", dataIndex: "id", width: 90 },
                { title: "分镜ID", dataIndex: "shot_id", width: 90 },
                { title: "类型", dataIndex: "media_type", width: 90 },
                { title: "状态", dataIndex: "status", width: 120 },
                {
                  title: "文件地址",
                  key: "play_url",
                  render: (_: unknown, row: SopMedia) => {
                    const href = sopFileDisplayUrl(row);
                    return href ? (
                      <a href={href} target="_blank" rel="noreferrer">
                        查看
                      </a>
                    ) : (
                      "-"
                    );
                  },
                },
              ]}
            />
            {!allMediaDone && (
              <div className="text-xs text-slate-500">
                仅当全部媒体状态为 success/completed/done/ready 时，“发布到 YouTube”按钮可用。
              </div>
            )}
          </div>
        </Card>
      </div>
      <Modal
        title="发布前校验"
        open={publishModalOpen}
        onCancel={() => setPublishModalOpen(false)}
        onOk={handlePublishYouTube}
        okText="确认发布"
        cancelText="取消"
        confirmLoading={publishing}
      >
        <div className="space-y-3">
          <div>
            <div className="text-xs text-slate-500 mb-1">选择媒体</div>
            <Select
              value={publishMediaId ?? undefined}
              onChange={(v) => setPublishMediaId(v)}
              options={mediaRows
                .filter((x) => Boolean(sopFileDisplayUrl(x)))
                .map((x) => ({ value: x.id, label: `媒体 ${x.id} | 分镜 ${x.shot_id} | ${x.status}` }))}
              className="w-full"
              placeholder="请选择要发布的媒体"
            />
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">标题</div>
            <Input value={publishTitle} onChange={(e) => setPublishTitle(e.target.value)} maxLength={100} />
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">描述</div>
            <TextArea
              rows={4}
              value={publishDescription}
              onChange={(e) => setPublishDescription(e.target.value)}
              maxLength={5000}
            />
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">隐私级别</div>
            <Select
              value={publishPrivacy}
              onChange={(v) => setPublishPrivacy(v)}
              options={[
                { value: "private", label: "private（私有）" },
                { value: "unlisted", label: "unlisted（不公开）" },
                { value: "public", label: "public（公开）" },
              ]}
              className="w-full"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}

function ShotEditableCard({
  shot,
  assets,
  saving,
  onChange,
  onUpload,
}: {
  shot: SopShot;
  assets: SopAsset[];
  saving: boolean;
  onChange: (shotId: number, patch: Partial<SopShot>) => void;
  onUpload: (shotId: number, file: File) => Promise<void>;
}) {
  const fileList: UploadFile[] = [];
  const { isOver, setNodeRef } = useDroppable({ id: `shot-drop-${shot.id}` });

  const renderAssetThumb = (asset: SopAsset) => {
    const url = sopFileDisplayUrl(asset);
    const pathHint = (asset.file_url || url).split("?")[0];
    const isVideo =
      asset.asset_type === "video" ||
      /\.(mp4|webm|mov|m4v)$/i.test(pathHint) ||
      /\.(mp4|webm|mov|m4v)$/i.test(asset.name);
    if (isVideo) {
      return <video src={url} className="w-full h-24 object-cover rounded border border-slate-200 bg-black" />;
    }
    if (url) {
      return <img src={url} alt={asset.name} className="w-full h-24 object-cover rounded border border-slate-200" />;
    }
    return <div className="w-full h-24 rounded border border-slate-200 bg-slate-100 flex items-center justify-center text-xs text-slate-500">无预览</div>;
  };

  return (
    <div className="border border-slate-200 rounded-lg bg-white p-3">
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-3">
        <div className="xl:col-span-3 flex flex-col min-h-[260px]">
          <div className="mb-2 flex items-center justify-between">
            <div className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-sm font-semibold text-slate-700">
              镜头 #{String(shot.shot_no).padStart(2, "0")}
            </div>
            {saving && <span className="text-xs text-slate-500">保存中...</span>}
          </div>
          <MarkdownEditorToggle
            className="flex-1"
            value={shot.visual_prompt || ""}
            onChange={(v) => onChange(shot.id, { visual_prompt: v })}
            minRows={12}
            placeholder="输入画面提示词（支持 Markdown）"
          />
        </div>

        <div
          ref={setNodeRef}
          className={`xl:col-span-2 rounded-md p-2 border transition-colors ${
            isOver ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-slate-50"
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="font-medium text-slate-800">资产与媒体</div>
            <div className="flex gap-2">
              <Upload
                fileList={fileList}
                showUploadList={false}
                beforeUpload={(file) => {
                  void onUpload(shot.id, file);
                  return false;
                }}
              >
                <Button size="small">上传素材</Button>
              </Upload>
              <Button size="small" onClick={() => message.info("重新生成画面功能将在下一阶段接入真实生成接口")}>
                重新生成画面
              </Button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {assets.map((a) => (
              <div key={a.id} className="rounded border border-slate-200 p-1">
                {renderAssetThumb(a)}
                <div className="text-xs text-slate-600 mt-1 truncate">{a.name}</div>
              </div>
            ))}
            {assets.length === 0 && (
              <div className="col-span-2 text-xs text-slate-500 border border-dashed border-slate-300 rounded p-3 text-center">
                暂无素材，点击“上传素材”
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DraggablePublicAsset({ asset }: { asset: SopAsset }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `public-asset-${asset.id}`,
  });
  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.6 : 1,
  };
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="rounded-lg border border-slate-200 bg-white p-2 cursor-grab active:cursor-grabbing"
    >
      <div className="text-sm text-slate-800 font-medium truncate">{asset.name}</div>
      <div className="text-xs text-slate-500 mt-1">类型：{asset.asset_type}</div>
      <div className="text-xs text-slate-500">来源资产ID：{asset.id}</div>
    </div>
  );
}

