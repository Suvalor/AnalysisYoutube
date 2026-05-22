import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  PointerSensor,
  closestCenter,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { Button, Card, message, Select, Spin, Typography } from "antd";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useBoardStore } from "@/store/useBoardStore";
import { listModelsApi, listPromptsApi, type ModelItem, type PromptItem } from "@/services/libraryApi";
import apiClient from "@/services/apiClient";

const { Text, Paragraph } = Typography;

type BoardTask = {
  id: number;
  title: string;
  status: string;
  order_index: number;
  due_date: string | null;
  script_id: number | null;
};

function taskId(taskIdValue: number) {
  return `task-${taskIdValue}`;
}

function columnId(status: string) {
  return `column-${status}`;
}

function parseDragId(id: string) {
  if (id.startsWith("task-")) return { type: "task" as const, value: Number(id.slice(5)) };
  if (id.startsWith("column-")) return { type: "column" as const, value: id.slice(7) };
  return { type: "unknown" as const, value: id };
}

function SortableTaskCard({ task, t }: { task: BoardTask; t: (key: string) => string }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: taskId(task.id),
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.7 : 1,
  };
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="rounded-xl border border-yc-border bg-yc-bg-column-card p-3 shadow-md cursor-grab active:cursor-grabbing"
    >
      <h4 className="font-medium text-yc-text-primary">{task.title}</h4>
      <div className="mt-2 text-xs text-yc-text-secondary space-y-1">
        <div>{t("board.dueDate")}{task.due_date ?? t("board.dueDateNotSet")}</div>
        {task.script_id ? <div>{t("board.linkedScript")}</div> : <div>{t("board.noLinkedScript")}</div>}
      </div>
    </div>
  );
}

function BoardColumn({
  status,
  title,
  tasks,
  onCreate,
  t,
}: {
  status: string;
  title: string;
  tasks: BoardTask[];
  onCreate: () => void;
  t: (key: string) => string;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: columnId(status) });
  return (
    <div className="w-[300px] shrink-0 rounded-2xl border border-yc-border bg-yc-bg-column p-3 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-yc-text-column">{title}</h3>
        <button onClick={onCreate} className="text-xs px-2 py-1 rounded bg-yc-bg-inset hover:bg-yc-bg-card text-yc-text-secondary">
          {t("board.newProject")}
        </button>
      </div>
      <div ref={setNodeRef} className={`min-h-[120px] space-y-2 rounded-xl p-1 transition-colors ${isOver ? "bg-yc-bg-inset" : ""}`}>
        <SortableContext items={tasks.map((t) => taskId(t.id))} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <SortableTaskCard key={task.id} task={task} t={t} />
          ))}
        </SortableContext>
      </div>
    </div>
  );
}

export default function VideoBoard() {
  const { t } = useTranslation("video");
  const { columns, tasks, fetchTasks, createTask, moveTask } = useBoardStore();
  const [creatingForStatus, setCreatingForStatus] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));
  // AI 建议
  const [aiSuggestion, setAiSuggestion] = useState<Record<string, string> | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [modelOptions, setModelOptions] = useState<ModelItem[]>([]);
  const [agentOptions, setAgentOptions] = useState<PromptItem[]>([]);
  const [selectedModelLibId, setSelectedModelLibId] = useState<number | undefined>(undefined);
  const [selectedLlmModelName, setSelectedLlmModelName] = useState<string>("");
  const [selectedAgentId, setSelectedAgentId] = useState<number | undefined>(undefined);

  useEffect(() => {
    const loadConfigs = async () => {
      try {
        const [models, prompts] = await Promise.all([listModelsApi(), listPromptsApi()]);
        const chatModels = models.filter((m) => (m.library_kind ?? "chat") === "chat");
        setModelOptions(chatModels);
        setAgentOptions(prompts);
        if (chatModels.length > 0) {
          const first = chatModels[0];
          const firstName = ((first.supported_models_json || "").match(/"value"\s*:\s*"([^"]+)"/)?.[1] ?? "").trim();
          setSelectedModelLibId(first.id);
          setSelectedLlmModelName(firstName);
        }
        if (prompts.length > 0) setSelectedAgentId(prompts[0].id);
      } catch { /* 静默 */ }
    };
    void loadConfigs();
  }, []);

  // 所有库的模型名扁平化选项，选项值格式："{libId}::{modelName}"
  const allModelNameOpts = useMemo(
    () =>
      modelOptions.flatMap((lib) => {
        try {
          const parsed: Array<{ value?: string; label?: string } | string> = JSON.parse(
            lib.supported_models_json || "[]"
          );
          return parsed.flatMap((m) => {
            const name = typeof m === "string" ? m : (m.value ?? "");
            const display = typeof m === "string" ? m : (m.label ?? m.value ?? "");
            if (!name) return [];
            return [{
              value: `${lib.id}::${name}`,
              label: modelOptions.length > 1 ? `${display} (${lib.name})` : display,
            }];
          });
        } catch {
          return [];
        }
      }),
    [modelOptions]
  );

  useEffect(() => {
    void fetchTasks();
  }, [fetchTasks]);

  const grouped = useMemo(() => {
    const map: Record<string, BoardTask[]> = {};
    columns.forEach((c: any) => {
      map[c.id] = (tasks as BoardTask[])
        .filter((t) => t.status === c.id)
        .sort((a, b) => a.order_index - b.order_index);
    });
    return map;
  }, [columns, tasks]);

  const handleDragOver = (_event: DragOverEvent) => {
    // 预留：如需拖拽中即时跨列预览，可在此添加轻量本地态逻辑
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    const activeParsed = parseDragId(String(active.id));
    const overParsed = parseDragId(String(over.id));
    if (activeParsed.type !== "task") return;

    const activeTask = (tasks as BoardTask[]).find((t) => t.id === activeParsed.value);
    if (!activeTask) return;

    let targetStatus = activeTask.status;
    let targetIndex = 0;

    if (overParsed.type === "column") {
      targetStatus = overParsed.value;
      targetIndex = grouped[targetStatus]?.length ?? 0;
    } else if (overParsed.type === "task") {
      const overTask = (tasks as BoardTask[]).find((t) => t.id === overParsed.value);
      if (!overTask) return;
      targetStatus = overTask.status;
      const list = grouped[targetStatus] || [];
      targetIndex = list.findIndex((t) => t.id === overTask.id);
      if (targetIndex < 0) targetIndex = list.length;
    }

    try {
      await moveTask(activeTask.id, targetStatus, targetIndex);
    } catch {
      message.error(t("board.moveTaskFailed"));
      await fetchTasks();
    }
  };

  const submitCreate = async (status: string) => {
    if (!newTitle.trim()) return;
    try {
      await createTask(newTitle.trim());
      setCreatingForStatus(null);
      setNewTitle("");
      if (status !== "idea") {
        const created = (useBoardStore.getState().tasks as BoardTask[]).find((t) => t.title === newTitle.trim());
        if (created) {
          await moveTask(created.id, status, grouped[status]?.length ?? 0);
        }
      }
    } catch {
      message.error(t("board.createTaskFailed"));
    }
  };

  const onAiSuggest = async () => {
    if (!selectedModelLibId || !selectedLlmModelName) {
      message.warning(t("board.selectModelFirst"));
      return;
    }
    setAiLoading(true);
    setAiSuggestion(null);
    try {
      const res = await apiClient.post("/api/video-projects/ai-suggest", {
        model_library_id: selectedModelLibId,
        llm_model_name: selectedLlmModelName,
        agent_id: selectedAgentId,
      });
      setAiSuggestion(res.data.suggestion);
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? t("board.aiSuggestFailed"));
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="p-6 md:p-8">
      {/* AI 策略建议区域 */}
      <Card className="!bg-yc-bg-card !border-yc-border !shadow-sm mb-6" title={t("board.aiSuggestTitle")}>
        <div className="flex items-center gap-3 flex-wrap mb-3">
          <Select
            showSearch
            style={{ width: 240 }}
            placeholder={t("board.selectModelPlaceholder")}
            value={
              selectedModelLibId !== undefined && selectedLlmModelName
                ? `${selectedModelLibId}::${selectedLlmModelName}`
                : undefined
            }
            onChange={(v: string) => {
              const idx = v.indexOf("::");
              setSelectedModelLibId(Number(v.slice(0, idx)));
              setSelectedLlmModelName(v.slice(idx + 2));
            }}
            options={allModelNameOpts}
            filterOption={(input, opt) =>
              String(opt?.label ?? "").toLowerCase().includes(input.toLowerCase())
            }
            allowClear
            onClear={() => { setSelectedModelLibId(undefined); setSelectedLlmModelName(""); }}
          />
          <Select
            style={{ width: 200 }}
            placeholder={t("board.selectAgentPlaceholder")}
            value={selectedAgentId}
            onChange={setSelectedAgentId}
            options={agentOptions.map((p) => ({ value: p.id, label: p.title }))}
            allowClear
          />
          <Button type="primary" loading={aiLoading} onClick={onAiSuggest}>
            {t("board.generateSuggestion")}
          </Button>
        </div>
        {aiLoading && <div className="flex justify-center py-4"><Spin tip={t("board.aiAnalyzing")} /></div>}
        {aiSuggestion && (
          <div className="space-y-3">
            {aiSuggestion.content_gaps && <div><Text strong>{t("board.contentGap")}</Text><Paragraph className="!mb-0">{aiSuggestion.content_gaps}</Paragraph></div>}
            {aiSuggestion.publishing_strategy && <div><Text strong>{t("board.publishStrategy")}</Text><Paragraph className="!mb-0">{aiSuggestion.publishing_strategy}</Paragraph></div>}
            {aiSuggestion.improvement_suggestions && <div><Text strong>{t("board.improvementSuggestion")}</Text><Paragraph className="!mb-0">{aiSuggestion.improvement_suggestions}</Paragraph></div>}
            {aiSuggestion.trend_opportunities && <div><Text strong>{t("board.trendOpportunity")}</Text><Paragraph className="!mb-0">{aiSuggestion.trend_opportunities}</Paragraph></div>}
          </div>
        )}
      </Card>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragOver={handleDragOver} onDragEnd={handleDragEnd}>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {(columns as any[]).map((col) => (
            <div key={col.id}>
              <BoardColumn
                status={col.id}
                title={col.title}
                tasks={grouped[col.id] || []}
                onCreate={() => setCreatingForStatus(col.id)}
                t={t}
              />
              {creatingForStatus === col.id && (
                <div className="mt-2 rounded-xl border border-yc-border bg-yc-bg-column-card p-3 w-[300px]">
                  <input
                    className="w-full rounded-md bg-yc-bg-column-input border border-yc-border px-3 py-2 text-sm"
                    placeholder={t("board.inputTitlePlaceholder")}
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                  />
                  <div className="flex justify-end gap-2 mt-2">
                    <button className="px-3 py-1 text-sm rounded bg-yc-bg-inset text-yc-text-secondary" onClick={() => setCreatingForStatus(null)}>
                      {t("board.cancel")}
                    </button>
                    <button className="px-3 py-1 text-sm rounded bg-yc-primary text-yc-text-inverse" onClick={() => submitCreate(col.id)}>
                      {t("board.create")}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </DndContext>
    </div>
  );
}