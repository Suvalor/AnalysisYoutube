import {
  BarChart3,
  Clapperboard,
  Cloud,
  Home,
  Image,
  Kanban,
  Library,
  Lightbulb,
  LogOut,
  Menu as MenuIcon,
  Settings,
  Video,
  WandSparkles,
  X,
  Youtube,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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
import FeishuWorkspace from "@/pages/feishu/FeishuWorkspace";
import AiModelSettings from "@/pages/settings/AiModelSettings";
import ConfigCenter from "@/pages/settings/ConfigCenter";
import AgentEditorPage from "@/pages/settings/AgentEditorPage";
import ScriptWorkflowSOP from "@/pages/sop/ScriptWorkflowSOP";
import InspirationPool from "@/pages/inspiration/InspirationPool";

/** 品牌色 Ant Design 主蓝，侧边栏 Logo 占位（无独立图片资源时使用） */
const BRAND_BLUE = "#1890ff";

function BrandMark() {
  return (
    <svg
      width={36}
      height={36}
      viewBox="0 0 36 36"
      className="shrink-0"
      aria-hidden
    >
      <rect x="2" y="2" width="32" height="32" rx="9" fill={BRAND_BLUE} fillOpacity={0.12} />
      <path
        d="M11 24 L18 9 L25 24 Z"
        fill="none"
        stroke={BRAND_BLUE}
        strokeWidth={2}
        strokeLinejoin="round"
      />
      <circle cx="18" cy="24" r="2.25" fill={BRAND_BLUE} />
    </svg>
  );
}

type NavDef = {
  path: string;
  label: string;
  icon: typeof Home;
  type: TabType;
  tabId: string;
};

/** 顺序：创作 → 管理 → 监控 → 系统 */
const navDefs: NavDef[] = [
  { path: "/inspiration-pool", label: "灵感中心", icon: Lightbulb, type: "inspiration-pool", tabId: "inspiration-pool" },
  { path: "/ai-creator", label: "AI 脚本工坊", icon: WandSparkles, type: "ai-creator", tabId: "ai-creator" },
  { path: "/sop-workflow", label: "SOP 工作流", icon: Clapperboard, type: "sop-workflow", tabId: "sop-workflow" },
  { path: "/assets", label: "素材库", icon: Image, type: "assets", tabId: "assets" },
  { path: "/knowledge-base", label: "知识库管理", icon: Library, type: "knowledge-base", tabId: "knowledge-base" },
  { path: "/youtube/channels", label: "频道管理", icon: Youtube, type: "channel-list", tabId: "channel-list" },
  { path: "/youtube/videos", label: "全局视频", icon: Video, type: "global-videos", tabId: "global-videos" },
  { path: "/video-board", label: "视频看板", icon: Kanban, type: "video-board", tabId: "video-board" },
  { path: "/competitor-analysis", label: "竞对洞察", icon: BarChart3, type: "competitor-analysis", tabId: "competitor-analysis" },
  { path: "/dashboard", label: "仪表盘", icon: Home, type: "dashboard", tabId: "dashboard" },
  { path: "/config-center", label: "设置中心", icon: Settings, type: "config-center", tabId: "config-center" },
  { path: "/feishu-workspace", label: "飞书云文档", icon: Cloud, type: "feishu-workspace", tabId: "feishu-workspace" },
];

function renderTabPanel(tab: TabItem) {
  switch (tab.type) {
    case "dashboard":
      return <Dashboard />;
    case "channel-list":
      return <ChannelList />;
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
    case "sop-workflow":
      return <ScriptWorkflowSOP />;
    case "inspiration-pool":
      return <InspirationPool />;
    case "competitor-analysis":
      return <CompetitorAnalysis />;
    case "feishu-workspace":
      return <FeishuWorkspace />;
    case "ai-model-settings":
      return <AiModelSettings />;
    case "config-center":
      return <ConfigCenter />;
    case "agent-edit":
      return <AgentEditorPage promptId={tab.promptId ?? Number((tab.path.match(/\/config\/agent\/edit\/(\d+)$/)?.[1] ?? 0))} />;
    case "youtube-quota":
    case "youtube-import":
      return <Dashboard />;
    default:
      return (
        <div className="p-6 text-slate-600 text-sm">
          无法识别该标签类型（{String(tab.type)}），请关闭标签后从左侧菜单重新打开对应页面。
        </div>
      );
  }
}

export default function TabbedShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setToken } = useAuth();
  const { tabs, activeTabId, openTab, closeTab, setActiveTab } = useTabStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (location.pathname === "/" || location.pathname === "") {
      navigate("/dashboard", { replace: true });
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
      openTab({ id: def.tabId, title: def.label, path: fullPath, type: def.type });
    }
    const m = path.match(/^\/youtube\/channel\/(\d+)$/);
    if (m) {
      const cid = Number(m[1]);
      openTab({
        id: `channel-detail-${cid}`,
        title: "博主详情",
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
        title: `编辑智能体 #${pid}`,
        path,
        type: "agent-edit",
        promptId: pid,
      });
    }
  }, [location.pathname, location.search, openTab]);

  const pageTitle = useMemo(() => {
    const tab = tabs.find((x) => x.id === activeTabId);
    return tab?.title ?? "Creator SaaS";
  }, [tabs, activeTabId]);

  const handleNav = (def: NavDef) => {
    openTab({ id: def.tabId, title: def.label, path: def.path, type: def.type });
    navigate(def.path);
    setMobileOpen(false);
  };

  const logout = () => {
    setToken(null);
    navigate("/login");
  };

  const SidebarContent = (
    <aside className="h-full bg-white border-r border-slate-200/90 shadow-[4px_0_24px_rgba(15,23,42,0.07)] flex flex-col">
      <div className="min-h-[4rem] px-4 py-3 flex items-center gap-3 border-b border-slate-200/90 shrink-0">
        <BrandMark />
        <div className="min-w-0 flex flex-col justify-center">
          <span className="font-semibold text-slate-900 text-[15px] leading-snug truncate">Creator SaaS</span>
          <span className="text-[11px] text-slate-500 leading-tight truncate">创作与增长工作台</span>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navDefs.map((def) => {
          const Icon = def.icon;
          const active = activeTabId === def.tabId;
          return (
            <button
              key={def.path}
              type="button"
              onClick={() => handleNav(def)}
              className={`w-full flex items-center gap-3 rounded-lg text-sm text-left transition-all duration-150 px-3 py-2.5 ${
                active
                  ? "bg-[#e6f4ff] text-[#1890ff] font-semibold shadow-sm ring-1 ring-[#1890ff]/15"
                  : "text-slate-700 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon size={18} className={active ? "opacity-100" : "opacity-85"} strokeWidth={active ? 2.25 : 2} />
              <span className="truncate">{def.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-slate-900 flex">
      <div className="hidden lg:block w-72 shrink-0">{SidebarContent}</div>

      <div className="flex-1 min-w-0 flex flex-col min-h-screen">
        <header className="h-16 border-b border-slate-200 bg-white px-4 md:px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-md hover:bg-slate-100"
              aria-label="打开侧边栏"
            >
              <MenuIcon size={18} />
            </button>
            <h1 className="text-base md:text-lg font-semibold truncate">{pageTitle}</h1>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center text-sm">U</div>
            <button
              type="button"
              onClick={logout}
              className="px-3 py-1.5 rounded-md bg-slate-900 text-white hover:bg-slate-700 text-sm flex items-center"
            >
              <LogOut size={14} className="mr-1.5" />
              登出
            </button>
          </div>
        </header>

        {/* 浏览器式标签栏 */}
        <div className="bg-slate-100 border-b border-slate-200 px-2 pt-2 flex gap-1 overflow-x-auto shrink-0">
          {tabs.map((tab) => {
            const active = tab.id === activeTabId;
            return (
              <div
                key={tab.id}
                className={`group flex items-center gap-1 max-w-[200px] rounded-t-md px-3 py-2 text-sm border border-b-0 cursor-pointer shrink-0 ${
                  active ? "bg-white border-slate-200 text-blue-700 font-medium" : "bg-slate-50/80 border-transparent text-slate-600"
                }`}
                onClick={() => {
                  setActiveTab(tab.id);
                  navigate(tab.path);
                }}
              >
                <span className="truncate">{tab.title}</span>
                <button
                  type="button"
                  className="p-0.5 rounded hover:bg-slate-200 opacity-70 hover:opacity-100"
                  aria-label="关闭标签"
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTab(tab.id);
                  }}
                >
                  <X size={14} />
                </button>
              </div>
            );
          })}
        </div>

        <main className="flex-1 min-h-0 overflow-hidden relative">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={tab.id === activeTabId ? "h-full overflow-y-auto" : "hidden"}
              aria-hidden={tab.id !== activeTabId}
            >
              {renderTabPanel(tab)}
            </div>
          ))}
        </main>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 h-full w-72">{SidebarContent}</div>
        </div>
      )}
    </div>
  );
}
