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
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useEffect, useMemo, useState } from "react";
import { useBoardStore } from "@/store/useBoardStore";

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

function SortableTaskCard({ task }: { task: BoardTask }) {
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
      className="rounded-xl border border-slate-700 bg-slate-900 p-3 shadow-md cursor-grab active:cursor-grabbing"
    >
      <h4 className="font-medium text-slate-100">{task.title}</h4>
      <div className="mt-2 text-xs text-slate-400 space-y-1">
        <div>截止日期：{task.due_date ?? "未设置"}</div>
        {task.script_id ? <div>已关联剧本</div> : <div>未关联剧本</div>}
      </div>
    </div>
  );
}

function BoardColumn({
  status,
  title,
  tasks,
  onCreate,
}: {
  status: string;
  title: string;
  tasks: BoardTask[];
  onCreate: () => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: columnId(status) });
  return (
    <div className="w-[300px] shrink-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-3 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">{title}</h3>
        <button onClick={onCreate} className="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700">
          + 新建项目
        </button>
      </div>
      <div ref={setNodeRef} className={`min-h-[120px] space-y-2 rounded-xl p-1 ${isOver ? "bg-slate-800/40" : ""}`}>
        <SortableContext items={tasks.map((t) => taskId(t.id))} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <SortableTaskCard key={task.id} task={task} />
          ))}
        </SortableContext>
      </div>
    </div>
  );
}

export default function VideoBoard() {
  const { columns, tasks, fetchTasks, createTask, moveTask } = useBoardStore();
  const [creatingForStatus, setCreatingForStatus] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

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
      // noop
    }
  };

  return (
    <div className="p-6 md:p-8">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragOver={handleDragOver} onDragEnd={handleDragEnd}>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {(columns as any[]).map((col) => (
            <div key={col.id}>
              <BoardColumn
                status={col.id}
                title={col.title}
                tasks={grouped[col.id] || []}
                onCreate={() => setCreatingForStatus(col.id)}
              />
              {creatingForStatus === col.id && (
                <div className="mt-2 rounded-xl border border-slate-800 bg-slate-900 p-3 w-[300px]">
                  <input
                    className="w-full rounded-md bg-slate-800 border border-slate-700 px-3 py-2 text-sm"
                    placeholder="输入项目标题"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                  />
                  <div className="flex justify-end gap-2 mt-2">
                    <button className="px-3 py-1 text-sm rounded bg-slate-700" onClick={() => setCreatingForStatus(null)}>
                      取消
                    </button>
                    <button className="px-3 py-1 text-sm rounded bg-indigo-500" onClick={() => submitCreate(col.id)}>
                      创建
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

