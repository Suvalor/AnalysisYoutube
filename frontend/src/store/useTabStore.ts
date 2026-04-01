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
  | "sop-workflow";

export type TabItem = {
  id: string;
  title: string;
  path: string;
  type: TabType;
  /** 仅 type 为 channel-detail 时使用 */
  channelId?: number;
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
