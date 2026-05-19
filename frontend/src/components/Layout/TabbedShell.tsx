import { Dropdown } from "antd";
import type { MenuProps } from "antd";
import {
  Activity,
  BarChart3,
  Clapperboard,
  Cloud,
  Compass,
  Download,
  Home,
  Image,
  Kanban,
  Library,
  Lightbulb,
  LogOut,
  Menu as MenuIcon,
  Search,
  Settings,
  TrendingUp,
  User,
  Video,
  WandSparkles,
  Waves,
  X,
  Youtube,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import i18n from "@/i18n";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/store/authStore";
import { useTabStore, type TabItem, type TabType } from "@/store/useTabStore";
import Dashboard from "@/pages/dashboard/Dashboard";
import AICreator from "@/pages/ai/AICreator";
import KnowledgeBase from "@/pages/knowledge/KnowledgeBase";
import AssetLibraryPage from "@/pages/knowledge/AssetLibrary";
import VideoBoard from "@/pages/board/VideoBoard";
import CompetitorAnalysis from "@/pages/youtube/CompetitorAnalysis";
import ChannelList from "@/pages/youtube/ChannelList";
import GlobalVideoList from "@/pages/youtube/GlobalVideoList";
import ChannelDetail from "@/pages/youtube/ChannelDetail";
import FeishuDocList from "@/pages/feishu/FeishuDocList";
import FeishuDocViewer from "@/pages/feishu/FeishuDocViewer";
import ConfigCenter from "@/pages/settings/ConfigCenter";
import PersonalSettings from "@/pages/settings/PersonalSettings";
import AgentEditorPage from "@/pages/settings/AgentEditorPage";
import ScriptWorkflowSOP from "@/pages/sop/ScriptWorkflowSOP";
import InspirationPool from "@/pages/inspiration/InspirationPool";
import BlueOceanRadar from "@/pages/radar/BlueOceanRadar";
import NavigationGuide from "@/pages/radar/NavigationGuide";
import KeywordResearch from "@/pages/keyword/KeywordResearch";
import SeoScoring from "@/pages/seo/SeoScoring";
import TrendDiscovery from "@/pages/trend/TrendDiscovery";
import ChannelGrowthDashboard from "@/pages/growth/ChannelGrowthDashboard";
import DownloadList from "@/pages/youtube/DownloadList";
import { isFeatureEnabled, hasRole, type FeatureKey } from "@/config/features";
import { UserRole } from "@/types/auth";
import { useThemeStore } from "@/store/useThemeStore";
import { useI18nStore } from "@/store/useI18nStore";
import { getUserSettingsApi } from "@/services/userApi";
import QuotaProgress from "@/components/QuotaProgress";
import GuestLimitModal from "@/components/GuestLimitModal";
import RequireRole from "@/components/RequireRole";
import { fetchGuestQuotaUsage, isGuestQuotaExhausted } from "@/services/guestService";
import type { QuotaUsage } from "@/types/auth";

function BrandMark() {
  return (
    <svg
      width={36}
      height={36}
      viewBox="0 0 36 36"
      className="shrink-0"
      aria-hidden
    >
      <rect x="2" y="2" width="32" height="32" rx="9" fill="var(--color-primary-bg)" />
      <path
        d="M11 24 L18 9 L25 24 Z"
        fill="none"
        stroke="var(--color-primary)"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      <circle cx="18" cy="24" r="2.25" fill="var(--color-primary)" />
    </svg>
  );
}

type NavDef = {
  path: string;
  labelKey: string;
  icon: typeof Home;
  type: TabType;
  tabId: string;
  featureKey?: FeatureKey;
  minRole?: UserRole;
};

/** 顺序：出海核心 -> 监控 -> 系统；创作者工具通过 Feature Flag + 角色控制 */
const navDefs: NavDef[] = [
  { path: "/dashboard", labelKey: "nav:dashboard", icon: Home, type: "dashboard", tabId: "dashboard", minRole: UserRole.ADMIN },
  { path: "/blue-ocean-radar", labelKey: "nav:blueOceanRadar", icon: Waves, type: "blue-ocean-radar", tabId: "blue-ocean-radar", minRole: UserRole.USER },
  { path: "/keyword-research", labelKey: "nav:keywordResearch", icon: Search, type: "keyword-research", tabId: "keyword-research", minRole: UserRole.GUEST },
  { path: "/seo-scoring", labelKey: "nav:seoScoring", icon: Zap, type: "seo-scoring", tabId: "seo-scoring", minRole: UserRole.GUEST },
  { path: "/trend-discovery", labelKey: "nav:trendDiscovery", icon: TrendingUp, type: "trend-discovery", tabId: "trend-discovery", minRole: UserRole.GUEST },
  { path: "/navigation-guide", labelKey: "nav:navigationGuide", icon: Compass, type: "navigation-guide", tabId: "navigation-guide", minRole: UserRole.USER },
  { path: "/competitor-analysis", labelKey: "nav:competitorAnalysis", icon: BarChart3, type: "competitor-analysis", tabId: "competitor-analysis", minRole: UserRole.USER },
  { path: "/channel-growth", labelKey: "nav:channelGrowth", icon: Activity, type: "channel-growth", tabId: "channel-growth", minRole: UserRole.USER },
  { path: "/youtube/channels", labelKey: "nav:channelManagement", icon: Youtube, type: "channel-list", tabId: "channel-list", minRole: UserRole.USER },
  { path: "/youtube/videos", labelKey: "nav:globalVideos", icon: Video, type: "global-videos", tabId: "global-videos", minRole: UserRole.USER },
  { path: "/video-board", labelKey: "nav:videoBoard", icon: Kanban, type: "video-board", tabId: "video-board", minRole: UserRole.USER },
  { path: "/downloads", labelKey: "nav:downloadManager", icon: Download, type: "download-list", tabId: "download-list", minRole: UserRole.USER },
  { path: "/config-center", labelKey: "nav:configCenter", icon: Settings, type: "config-center", tabId: "config-center", minRole: UserRole.USER },
  // 创作者工具（Feature Flag + 角色控制，PRD 6.1 要求仅管理员可见）
  { path: "/inspiration-pool", labelKey: "nav:inspirationPool", icon: Lightbulb, type: "inspiration-pool", tabId: "inspiration-pool", featureKey: "INSPIRATION_POOL", minRole: UserRole.ADMIN },
  { path: "/ai-creator", labelKey: "nav:aiCreator", icon: WandSparkles, type: "ai-creator", tabId: "ai-creator", featureKey: "AI_CREATOR", minRole: UserRole.ADMIN },
  { path: "/sop-workflow", labelKey: "nav:sopWorkflow", icon: Clapperboard, type: "sop-workflow", tabId: "sop-workflow", featureKey: "SOP_WORKFLOW", minRole: UserRole.ADMIN },
  { path: "/assets", labelKey: "nav:assetLibrary", icon: Image, type: "assets", tabId: "assets", featureKey: "ASSET_LIBRARY", minRole: UserRole.ADMIN },
  { path: "/knowledge-base", labelKey: "nav:knowledgeBase", icon: Library, type: "knowledge-base", tabId: "knowledge-base", featureKey: "KNOWLEDGE_BASE", minRole: UserRole.ADMIN },
  { path: "/feishu-workspace", labelKey: "nav:feishuWorkspace", icon: Cloud, type: "feishu-workspace", tabId: "feishu-workspace", featureKey: "FEISHU_DOCS", minRole: UserRole.ADMIN },
];

/** 标签页类型到最低角色的映射，用于页面级权限守卫。
 * 从 navDefs 自动派生，避免 DRY 违规；动态标签页（不在侧边栏导航中）需手动补充。 */
const TAB_MIN_ROLE: Partial<Record<TabType, UserRole>> = {
  ...Object.fromEntries(
    navDefs.filter(d => d.minRole).map(d => [d.type, d.minRole!])
  ),
  // 动态标签页守卫：这些标签页不在 navDefs 中，需手动补充纵深防御
  "agent-edit": UserRole.USER,
  "personal-settings": UserRole.USER,
};

/** 根据标签页类型渲染对应的页面组件 */
function renderTabPanel(tab: TabItem) {
  switch (tab.type) {
    case "dashboard":
      return <Dashboard />;
    case "channel-list":
      return <ChannelList />;
    case "blue-ocean-radar":
      return <BlueOceanRadar />;
    case "keyword-research":
      return <KeywordResearch />;
    case "global-videos":
      return <GlobalVideoList />;
    case "channel-detail":
      return <ChannelDetail channelId={tab.channelId!} />;
    case "ai-creator":
      return <AICreator />;
    case "knowledge-base":
      return <KnowledgeBase />;
    case "assets":
      return <AssetLibraryPage />;
    case "video-board":
      return <VideoBoard />;
    case "download-list":
      return <DownloadList />;
    case "sop-workflow":
      return <ScriptWorkflowSOP />;
    case "inspiration-pool":
      return <InspirationPool />;
    case "competitor-analysis":
      return <CompetitorAnalysis />;
    case "seo-scoring":
      return <SeoScoring />;
    case "trend-discovery":
      return <TrendDiscovery />;
    case "channel-growth":
      return <ChannelGrowthDashboard />;
    case "navigation-guide":
      return <NavigationGuide />;
    case "feishu-workspace":
      return <FeishuDocList />;
    case "feishu-viewer":
      return <FeishuDocViewer docId={tab.feishuDocId} />;
    case "config-center":
      return <ConfigCenter />;
    case "personal-settings":
      return <PersonalSettings />;
    case "agent-edit":
      return <AgentEditorPage promptId={tab.promptId ?? Number((tab.path.match(/\/config\/agent\/edit\/(\d+)$/)?.[1] ?? 0))} />;
    case "youtube-quota":
    case "youtube-import":
      return <Dashboard />;
    default:
      return (
        <div className="p-6 text-sm" style={{ color: "var(--color-text-secondary)" }}>
          {i18n.t("nav:unknownTab", { type: String(tab.type) })}
        </div>
      );
  }
}

export default function TabbedShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation(["nav", "common"]);
  const { role, token, setToken, quotaUsage } = useAuth();
  const {
    tabs,
    activeTabId,
    pinnedTabIds,
    openTab,
    closeTab,
    setActiveTab,
    closeLeftTabs,
    closeRightTabs,
    closeOtherTabs,
    closeAllTabs,
    registerPinnedIds,
  } = useTabStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  /** 游客配额弹窗状态 */
  const [guestLimitOpen, setGuestLimitOpen] = useState(false);
  const [guestQuotaUsage, setGuestQuotaUsage] = useState<QuotaUsage | null>(null);

  /** 游客模式下初始化配额数据，配额耗尽时自动弹出提示 */
  useEffect(() => {
    if (token) return;
    let mounted = true;
    (async () => {
      try {
        const usage = await fetchGuestQuotaUsage();
        if (mounted) {
          setGuestQuotaUsage(usage);
          if (isGuestQuotaExhausted(usage)) {
            setGuestLimitOpen(true);
          }
        }
      } catch {
        // 配额接口不可用时静默处理
      }
    })();
    return () => {
      mounted = false;
    };
  }, [token]);

  /** 监听 429 配额耗尽全局事件，自动弹出 GuestLimitModal */
  useEffect(() => {
    const handleQuotaExhausted = () => {
      setGuestLimitOpen(true);
    };
    window.addEventListener("quota-exhausted", handleQuotaExhausted);
    return () => {
      window.removeEventListener("quota-exhausted", handleQuotaExhausted);
    };
  }, []);

  // 启动时从后端同步主题和语言偏好（仅已登录用户）
  const syncFromServer = useThemeStore((s) => s.syncFromServer);
  const syncLocaleFromServer = useI18nStore((s) => s.syncFromServer);
  useEffect(() => {
    /** 未登录时跳过 API 调用，避免游客模式触发 401 */
    if (!token) return;
    let mounted = true;
    (async () => {
      try {
        const data = await getUserSettingsApi();
        if (mounted) {
          if (data.theme) syncFromServer(data.theme);
          if (data.locale) syncLocaleFromServer(data.locale);
        }
      } catch {
        // 加载失败时使用本地缓存
      }
    })();
    return () => {
      mounted = false;
    };
  }, [token, syncFromServer, syncLocaleFromServer]);

  // 初始化固定标签 ID 集合（navDefs 中的标签为固定标签，不可被批量关闭）
  useEffect(() => {
    registerPinnedIds(navDefs.map((d) => d.tabId));
  }, [registerPinnedIds]);

  // 批量关闭后，若活跃标签已变则自动导航
  // 当 openTab 改变 activeTabId 时（由 location useEffect 触发），
  // _suppressNavigation 为 true，跳过导航以避免反复横跳
  useEffect(() => {
    if (!activeTabId) return;
    // openTab 触发的 activeTabId 变化 → 不导航（location 已经是目标路径）
    if (useTabStore.getState()._suppressNavigation) {
      useTabStore.setState({ _suppressNavigation: false });
      return;
    }
    const activeTab = tabs.find((t) => t.id === activeTabId);
    // 只比较 pathname 部分，忽略 search params（tab.path 可能含 ?tab=xxx）
    if (activeTab && location.pathname !== activeTab.path.split("?")[0]) {
      navigate(activeTab.path);
    }
  }, [activeTabId, tabs, navigate, location.pathname]);

  useEffect(() => {
    if (location.pathname === "/" || location.pathname === "") {
      navigate("/blue-ocean-radar", { replace: true });
      return;
    }
    // 兼容旧链接：YouTube API 仪表盘已合并到仪表盘
    if (location.pathname === "/youtube-quota") {
      navigate("/dashboard", { replace: true });
    }
  }, [location.pathname, navigate]);

  useEffect(() => {
    const path = location.pathname;
    const fullPath = location.search ? `${path}${location.search}` : path;
    const def = navDefs.find((n) => n.path === path);
    if (def) {
      openTab({ id: def.tabId, title: t(def.labelKey), path: fullPath, type: def.type });
    }
    const m = path.match(/^\/youtube\/channel\/(\d+)$/);
    if (m) {
      const cid = Number(m[1]);
      openTab({
        id: `channel-detail-${cid}`,
        title: t("nav:channelDetail"),
        path: path,
        type: "channel-detail",
        channelId: cid,
      });
    }
    const editPromptMatch = path.match(/^\/config\/agent\/edit\/(\d+)$/);
    if (editPromptMatch) {
      const pid = Number(editPromptMatch[1]);
      openTab({
        id: `agent-edit-${pid}`,
        title: `${t("nav:agentEdit")} #${pid}`,
        path,
        type: "agent-edit",
        promptId: pid,
      });
    }
    const feishuViewMatch = path.match(/^\/feishu\/view\/(\d+)$/);
    if (feishuViewMatch) {
      const did = Number(feishuViewMatch[1]);
      openTab({
        id: `feishu-view-${did}`,
        title: t("nav:feishuViewer"),
        path,
        type: "feishu-viewer",
        feishuDocId: did,
      });
    }
  }, [location.pathname, location.search, openTab]);

  const pageTitle = useMemo(() => {
    const tab = tabs.find((x) => x.id === activeTabId);
    return tab?.title ?? "YouTube Compass";
  }, [tabs, activeTabId]);

  const handleNav = (def: NavDef) => {
    openTab({ id: def.tabId, title: t(def.labelKey), path: def.path, type: def.type });
    navigate(def.path);
    setMobileOpen(false);
  };

  const logout = () => {
    setToken(null);
    navigate("/login");
  };

  const SidebarContent = (
    <aside
      className="h-full flex flex-col"
      style={{
        backgroundColor: "var(--color-bg-sidebar)",
        borderRight: "1px solid var(--color-border)",
        boxShadow: "var(--shadow-sidebar)",
        backgroundImage: "var(--gradient-sidebar)",
        backdropFilter: "blur(var(--glass-blur))",
      }}
    >
      <div
        className="min-h-[4rem] px-4 py-3 flex items-center gap-3 shrink-0"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <BrandMark />
        <div className="min-w-0 flex flex-col justify-center">
          <span
            className="font-semibold text-[15px] leading-snug truncate"
            style={{ color: "var(--color-text-primary)" }}
          >
            YouTube Compass
          </span>
          <span
            className="text-[11px] leading-tight truncate"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {t("common:app.subtitle")}
          </span>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navDefs
          .filter((def) => (!def.featureKey || isFeatureEnabled(def.featureKey)) && (!def.minRole || hasRole(role, def.minRole)))
          .map((def) => {
          const Icon = def.icon;
          const active = activeTabId === def.tabId;
          return (
            <button
              key={def.path}
              type="button"
              onClick={() => handleNav(def)}
              className="w-full flex items-center gap-3 rounded-lg text-sm text-left transition-all duration-150 px-3 py-2.5"
              style={{
                backgroundColor: active ? "var(--color-primary-bg)" : "transparent",
                color: active ? "var(--color-primary)" : "var(--color-text-secondary)",
                fontWeight: active ? 600 : 400,
                boxShadow: active ? "0 1px 2px rgba(0,0,0,0.05)" : "none",
                outline: active ? "1px solid var(--color-primary-border)" : "none",
              }}
            >
              <Icon size={18} className={active ? "opacity-100" : "opacity-85"} strokeWidth={active ? 2.25 : 2} />
              <span className="truncate">{t(def.labelKey)}</span>
            </button>
          );
        })}
      </nav>
      {/* 已登录用户显示配额进度摘要 */}
      {token && quotaUsage && (
        <div
          className="px-4 py-3 shrink-0"
          style={{ borderTop: "1px solid var(--color-border)" }}
        >
          <QuotaProgress usage={quotaUsage} />
        </div>
      )}
    </aside>
  );

  return (
    <div
      className="min-h-screen flex"
      style={{ backgroundColor: "var(--color-bg-layout)", color: "var(--color-text-primary)" }}
    >
      <div className="hidden lg:block w-72 shrink-0">{SidebarContent}</div>

      <div className="flex-1 min-w-0 flex flex-col min-h-screen">
        <header
          className="h-16 px-4 md:px-6 flex items-center justify-between shrink-0"
          style={{
            borderBottom: "1px solid var(--color-border)",
            backgroundColor: "var(--color-bg-header)",
            backgroundImage: "var(--gradient-header)",
          }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-md"
              style={{ color: "var(--color-text-secondary)" }}
              aria-label="打开侧边栏"
            >
              <MenuIcon size={18} />
            </button>
            <h1
              className="text-base md:text-lg font-semibold truncate"
              style={{ color: "var(--color-text-primary)" }}
            >
              {pageTitle}
            </h1>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {token ? (
              <Dropdown
                menu={{
                  items: [
                    {
                      key: "personal-settings",
                      icon: <User size={14} />,
                      label: t("nav:personalSettings"),
                      onClick: () => {
                        openTab({
                          id: "personal-settings",
                          title: t("nav:personalSettings"),
                          path: "/personal-settings",
                          type: "personal-settings",
                        });
                        navigate("/personal-settings");
                      },
                    },
                    {
                      type: "divider",
                    },
                    {
                      key: "logout",
                      icon: <LogOut size={14} />,
                      label: t("common:action.logout"),
                      danger: true,
                      onClick: logout,
                    },
                  ],
                }}
                trigger={["click"]}
              >
                <button
                  type="button"
                  className="h-8 w-8 rounded-full flex items-center justify-center text-sm cursor-pointer"
                  style={{
                    backgroundColor: "var(--color-bg-inset)",
                    color: "var(--color-text-secondary)",
                  }}
                  aria-label="用户菜单"
                >
                  U
                </button>
              </Dropdown>
            ) : (
              <button
                type="button"
                className="px-3 py-1.5 rounded-md text-sm cursor-pointer"
                style={{
                  backgroundColor: "var(--color-primary)",
                  color: "#fff",
                }}
                onClick={() => navigate("/login")}
              >
                {t("common:action.login")}
              </button>
            )}
          </div>
        </header>

        {/* 浏览器式标签栏 */}
        <div
          className="px-2 pt-2 flex gap-1 overflow-x-auto shrink-0"
          style={{
            backgroundColor: "var(--color-bg-layout)",
            borderBottom: "1px solid var(--color-border)",
          }}
        >
          {tabs.map((tab) => {
            const active = tab.id === activeTabId;
            const tabIdx = tabs.findIndex((t) => t.id === tab.id);
            const isPinned = pinnedTabIds.has(tab.id);
            // 计算各菜单项是否可用
            const leftCount = tabs.slice(0, tabIdx).filter((t) => !pinnedTabIds.has(t.id)).length;
            const rightCount = tabs.slice(tabIdx + 1).filter((t) => !pinnedTabIds.has(t.id)).length;
            const otherCount = tabs.filter((t) => t.id !== tab.id && !pinnedTabIds.has(t.id)).length;
            const allCount = tabs.filter((t) => !pinnedTabIds.has(t.id)).length;

            const contextItems: MenuProps["items"] = [
              { key: "close-left", label: t("nav:tabClose.closeLeft"), disabled: leftCount === 0 },
              { key: "close-right", label: t("nav:tabClose.closeRight"), disabled: rightCount === 0 },
              { key: "close-others", label: t("nav:tabClose.closeOthers"), disabled: otherCount === 0 },
              { key: "close-all", label: t("nav:tabClose.closeAll"), disabled: allCount === 0 },
            ];

            const handleContextClick: MenuProps["onClick"] = ({ key }) => {
              switch (key) {
                case "close-left":
                  closeLeftTabs(tab.id);
                  break;
                case "close-right":
                  closeRightTabs(tab.id);
                  break;
                case "close-others":
                  closeOtherTabs(tab.id);
                  break;
                case "close-all":
                  closeAllTabs();
                  break;
              }
            };

            return (
              <Dropdown
                key={tab.id}
                menu={{ items: contextItems, onClick: handleContextClick }}
                trigger={["contextMenu"]}
              >
                <div
                  className="group flex items-center gap-1 max-w-[200px] rounded-t-md px-3 py-2 text-sm border border-b-0 cursor-pointer shrink-0 select-none"
                  style={{
                    backgroundColor: active ? "var(--color-bg-tab-active)" : "var(--color-bg-tab)",
                    borderColor: active ? "var(--color-border)" : "transparent",
                    color: active ? "var(--color-primary)" : "var(--color-text-secondary)",
                    fontWeight: active ? 500 : 400,
                  }}
                  onClick={() => {
                    setActiveTab(tab.id);
                    navigate(tab.path);
                  }}
                >
                  <span className="truncate">{tab.title}</span>
                  <button
                    type="button"
                    className="p-0.5 rounded opacity-70 hover:opacity-100"
                    style={{ backgroundColor: "var(--color-bg-inset)" }}
                    aria-label="关闭标签"
                    onClick={(e) => {
                      e.stopPropagation();
                      closeTab(tab.id);
                    }}
                  >
                    <X size={14} />
                  </button>
                </div>
              </Dropdown>
            );
          })}
        </div>

        <main className="flex-1 min-h-0 overflow-hidden relative">
          {tabs.map((tab) => {
            /** 页面级权限守卫：根据标签页类型查找最低角色要求 */
            const minRole = TAB_MIN_ROLE[tab.type];
            const content = renderTabPanel(tab);
            return (
              <div
                key={tab.id}
                className={tab.id === activeTabId ? "h-full overflow-y-auto" : "hidden"}
                aria-hidden={tab.id !== activeTabId}
              >
                {minRole ? (
                  <RequireRole requiredRole={minRole}>{content}</RequireRole>
                ) : (
                  content
                )}
              </div>
            );
          })}
        </main>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 h-full w-72">{SidebarContent}</div>
        </div>
      )}

      {/* 游客配额耗尽弹窗 */}
      <GuestLimitModal
        open={guestLimitOpen}
        onClose={() => setGuestLimitOpen(false)}
        usage={guestQuotaUsage}
      />
    </div>
  );
}
