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
  | "feishu-viewer"
  | "config-center"
  | "sop-workflow"
  | "agent-edit"
  | "inspiration-pool"
  | "blue-ocean-radar"
  | "keyword-research"
  | "seo-scoring"
  | "trend-discovery"
  | "navigation-guide"
  | "personal-settings"
  | "channel-growth"
  | "download-list";

export type TabItem = {
  id: string;
  title: string;
  path: string;
  type: TabType;
  /** 仅 type 为 channel-detail 时使用 */
  channelId?: number;
  /** 仅 type 为 agent-edit 时使用 */
  promptId?: number;
  /** 仅 type 为 feishu-viewer 时使用 */
  feishuDocId?: number;
};

type TabState = {
  tabs: TabItem[];
  activeTabId: string | null;
  /** 固定标签 ID 集合（来自 navDefs 的标签不可被批量关闭） */
  pinnedTabIds: Set<string>;
  openTab: (tab: TabItem) => void;
  closeTab: (id: string) => void;
  setActiveTab: (id: string) => void;
  /** 关闭目标标签左侧的所有非固定标签 */
  closeLeftTabs: (id: string) => void;
  /** 关闭目标标签右侧的所有非固定标签 */
  closeRightTabs: (id: string) => void;
  /** 关闭除目标标签外的所有非固定标签 */
  closeOtherTabs: (id: string) => void;
  /** 关闭所有非固定标签 */
  closeAllTabs: () => void;
  /** 注册固定标签 ID（由 TabbedShell 初始化时调用） */
  registerPinnedIds: (ids: string[]) => void;
};

export const useTabStore = create<TabState>((set, get) => ({
  tabs: [],
  activeTabId: null,
  pinnedTabIds: new Set<string>(),

  registerPinnedIds: (ids) => {
    set({ pinnedTabIds: new Set(ids) });
  },

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

  closeLeftTabs: (id) => {
    const { tabs, activeTabId, pinnedTabIds } = get();
    const idx = tabs.findIndex((t) => t.id === id);
    if (idx <= 0) return;
    // 保留目标及右侧所有标签，左侧仅保留固定标签
    const next = tabs.filter((t, i) => i >= idx || pinnedTabIds.has(t.id));
    const nextActive = next.some((t) => t.id === activeTabId) ? activeTabId : id;
    set({ tabs: next, activeTabId: nextActive });
  },

  closeRightTabs: (id) => {
    const { tabs, activeTabId, pinnedTabIds } = get();
    const idx = tabs.findIndex((t) => t.id === id);
    if (idx < 0 || idx === tabs.length - 1) return;
    // 保留目标及左侧所有标签，右侧仅保留固定标签
    const next = tabs.filter((t, i) => i <= idx || pinnedTabIds.has(t.id));
    const nextActive = next.some((t) => t.id === activeTabId) ? activeTabId : id;
    set({ tabs: next, activeTabId: nextActive });
  },

  closeOtherTabs: (id) => {
    const { tabs, activeTabId, pinnedTabIds } = get();
    // 保留目标标签 + 所有固定标签
    const next = tabs.filter((t) => t.id === id || pinnedTabIds.has(t.id));
    set({ tabs: next, activeTabId: id });
  },

  closeAllTabs: () => {
    const { tabs, pinnedTabIds } = get();
    // 仅保留固定标签
    const next = tabs.filter((t) => pinnedTabIds.has(t.id));
    const nextActive = next[0]?.id ?? null;
    set({ tabs: next, activeTabId: nextActive });
  },
}));
