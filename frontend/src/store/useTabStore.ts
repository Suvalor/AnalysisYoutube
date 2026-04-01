import { create } from "zustand";

/** 主工作区 Tab 类型（与左侧菜单、路由 path 对应） */
export type TabType =
  | "dashboard"
  | "channel-list"
  | "global-videos"
  | "channel-detail"
  | "youtube-quota"
  | "youtube-import"
  | "competitor-analysis"
  | "ai-creator"
  | "knowledge-base"
  | "assets"
  | "video-board"
  | "feishu-workspace"
  | "ai-model-settings"
  | "config-center"
  | "sop-workflow"
  | "agent-edit";

export type TabItem = {
  id: string;
  title: string;
  path: string;
  type: TabType;
  /** 仅 type 为 channel-detail 时使用 */
  channelId?: number;
  /** 仅 type 为 agent-edit 时使用 */
  promptId?: number;
};

type TabState = {
  tabs: TabItem[];
  activeTabId: string | null;
  openTab: (tab: TabItem) => void;
  closeTab: (id: string) => void;
  setActiveTab: (id: string) => void;
};

export const useTabStore = create<TabState>((set, get) => ({
  tabs: [],
  activeTabId: null,

  openTab: (tab) => {
    const { tabs } = get();

    // 同一智能体编辑页只保留一个标签：按 promptId / 路径合并，避免重复打开
    if (tab.type === "agent-edit" && typeof tab.promptId === "number" && Number.isFinite(tab.promptId)) {
      const pid = tab.promptId;
      const dupIdx = tabs.findIndex((t) => {
        if (t.type !== "agent-edit") return false;
        if (t.promptId === pid) return true;
        const m = t.path.match(/^\/config\/agent\/edit\/(\d+)$/);
        return m != null && Number(m[1]) === pid;
      });
      if (dupIdx >= 0) {
        const existing = tabs[dupIdx];
        const mergedId = existing.id;
        const nextTabs = tabs.map((t, i) =>
          i === dupIdx
            ? {
                ...t,
                ...tab,
                id: mergedId,
                type: "agent-edit" as const,
                promptId: pid,
                path: tab.path,
                title: tab.title,
              }
            : t
        );
        set({ tabs: nextTabs, activeTabId: mergedId });
        return;
      }
    }

    const idx = tabs.findIndex((t) => t.id === tab.id);
    if (idx >= 0) {
      set({ activeTabId: tab.id });
      return;
    }
    set({ tabs: [...tabs, tab], activeTabId: tab.id });
  },

  closeTab: (id) => {
    const { tabs, activeTabId } = get();
    const next = tabs.filter((t) => t.id !== id);
    let nextActive = activeTabId;
    if (activeTabId === id) {
      const closedIdx = tabs.findIndex((t) => t.id === id);
      const fallback = next[Math.max(0, closedIdx - 1)] ?? next[0];
      nextActive = fallback ? fallback.id : null;
    }
    set({ tabs: next, activeTabId: nextActive });
  },

  setActiveTab: (id) => set({ activeTabId: id }),
}));
