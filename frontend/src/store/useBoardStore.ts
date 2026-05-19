import { create } from "zustand";
import apiClient from "../services/apiClient";

/** 看板任务数据结构 */
type BoardTaskItem = {
  id: number;
  title: string;
  status: string;
  order_index: number;
};

/** 看板列定义 */
type BoardColumn = {
  id: string;
  title: string;
};

export const BOARD_COLUMNS: BoardColumn[] = [
  { id: "idea", title: "构思中 (Idea)" },
  { id: "scripting", title: "写本中 (Scripting)" },
  { id: "shooting", title: "拍摄中 (Shooting)" },
  { id: "editing", title: "剪辑中 (Editing)" },
  { id: "completed", title: "已完成 (Completed)" },
];

/** 按列分组并重排 order_index */
function normalizeOrders(tasks: BoardTaskItem[]): BoardTaskItem[] {
  const grouped = BOARD_COLUMNS.reduce<Record<string, BoardTaskItem[]>>((acc, col) => {
    acc[col.id] = tasks.filter((t) => t.status === col.id).sort((a, b) => a.order_index - b.order_index);
    return acc;
  }, {});
  const result: BoardTaskItem[] = [];
  for (const col of BOARD_COLUMNS) {
    grouped[col.id].forEach((task, index) => {
      result.push({ ...task, order_index: index });
    });
  }
  return result;
}

type BoardState = {
  columns: BoardColumn[];
  tasks: BoardTaskItem[];
  fetchTasks: () => Promise<void>;
  createTask: (title: string) => Promise<void>;
  moveTask: (activeTaskId: number, targetStatus: string, targetIndex: number) => Promise<void>;
};

export const useBoardStore = create<BoardState>((set, get) => ({
  columns: BOARD_COLUMNS,
  tasks: [],

  /** 从后端拉取看板任务列表 */
  fetchTasks: async () => {
    const res = await apiClient.get("/api/video-projects");
    set({ tasks: normalizeOrders(res.data || []) });
  },

  /** 创建新看板任务 */
  createTask: async (title: string) => {
    const res = await apiClient.post("/api/video-projects", {
      title,
      status: "idea",
    });
    set((state) => ({
      tasks: normalizeOrders([...state.tasks, res.data]),
    }));
  },

  /** 拖拽移动看板任务到目标列和位置 */
  moveTask: async (activeTaskId: number, targetStatus: string, targetIndex: number) => {
    const current = [...get().tasks];
    const activeIndex = current.findIndex((t) => t.id === activeTaskId);
    if (activeIndex === -1) return;

    const activeTask = { ...current[activeIndex], status: targetStatus };
    current.splice(activeIndex, 1);

    const columnTasks = current
      .filter((t) => t.status === targetStatus)
      .sort((a, b) => a.order_index - b.order_index);

    const insertIndex = Math.max(0, Math.min(targetIndex, columnTasks.length));
    columnTasks.splice(insertIndex, 0, activeTask);

    const otherTasks = current.filter((t) => t.status !== targetStatus);
    const merged = normalizeOrders([...otherTasks, ...columnTasks]);

    set({ tasks: merged });

    const payload = merged.map((item) => ({
      id: item.id,
      status: item.status,
      order_index: item.order_index,
    }));
    await apiClient.put("/api/video-projects/reorder", payload);
  },
}));
