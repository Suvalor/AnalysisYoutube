import { create } from "zustand";
import apiClient from "../services/apiClient";

export const BOARD_COLUMNS = [
  { id: "idea", title: "构思中 (Idea)" },
  { id: "scripting", title: "写本中 (Scripting)" },
  { id: "shooting", title: "拍摄中 (Shooting)" },
  { id: "editing", title: "剪辑中 (Editing)" },
  { id: "completed", title: "已完成 (Completed)" },
];

function normalizeOrders(tasks) {
  const grouped = BOARD_COLUMNS.reduce((acc, col) => {
    acc[col.id] = tasks.filter((t) => t.status === col.id).sort((a, b) => a.order_index - b.order_index);
    return acc;
  }, {});
  const result = [];
  for (const col of BOARD_COLUMNS) {
    grouped[col.id].forEach((task, index) => {
      result.push({ ...task, order_index: index });
    });
  }
  return result;
}

export const useBoardStore = create((set, get) => ({
  columns: BOARD_COLUMNS,
  tasks: [],

  fetchTasks: async () => {
    const res = await apiClient.get("/api/video-projects");
    set({ tasks: normalizeOrders(res.data || []) });
  },

  createTask: async (title) => {
    const res = await apiClient.post("/api/video-projects", {
      title,
      status: "idea",
    });
    set((state) => ({
      tasks: normalizeOrders([...state.tasks, res.data]),
    }));
  },

  moveTask: async (activeTaskId, targetStatus, targetIndex) => {
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

