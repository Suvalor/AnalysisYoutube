import {
  BarChart3,
  Home,
  Image,
  Kanban,
  Library,
  LogOut,
  Menu as MenuIcon,
  Settings,
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
import ScriptWorkflowSOP from "@/pages/sop/ScriptWorkflowSOP";

type NavDef = {
  path: string;
  label: string;
  icon: typeof Home;
  type: TabType;
  tabId: string;
};

const navDefs: NavDef[] = [
  { path: "/dashboard", label: "仪表盘", icon: Home, type: "dashboard", tabId: "dashboard" },
  { path: "/youtube/channels", label: "频道管理", icon: Youtube, type: "channel-list", tabId: "channel-list" },
  { path: "/youtube/videos", label: "全局视频", icon: Youtube, type: "global-videos", tabId: "global-videos" },
  { path: "/ai-creator", label: "AI 剧本创作", icon: WandSparkles, type: "ai-creator", tabId: "ai-creator" },
  { path: "/config-center", label: "配置中心", icon: Settings, type: "config-center", tabId: "config-center" },
  { path: "/knowledge-base", label: "知识库管理", icon: Library, type: "knowledge-base", tabId: "knowledge-base" },
  { path: "/assets", label: "素材库", icon: Image, type: "assets", tabId: "assets" },
  { path: "/video-board", label: "视频看板", icon: Kanban, type: "video-board", tabId: "video-board" },
  { path: "/sop-workflow", label: "SOP 工作流", icon: Kanban, type: "sop-workflow", tabId: "sop-workflow" },
  { path: "/competitor-analysis", label: "对标图表", icon: BarChart3, type: "competitor-analysis", tabId: "competitor-analysis" },
  { path: "/feishu-workspace", label: "飞书云文档", icon: Library, type: "feishu-workspace", tabId: "feishu-workspace" },
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
    case "competitor-analysis":
      return <CompetitorAnalysis />;
    case "feishu-workspace":
      return <FeishuWorkspace />;
    case "ai-model-settings":
      return <AiModelSettings />;
    case "config-center":
      return <ConfigCenter />;
    default:
      return null;
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
    const def = navDefs.find((n) => n.path === path);
    if (def) {
      openTab({ id: def.tabId, title: def.label, path: def.path, type: def.type });
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
  }, [location.pathname, openTab]);

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
    <aside className="h-full bg-white border-r border-slate-200 flex flex-col">
      <div className="h-16 px-4 flex items-center border-b border-slate-200">
        <div className="h-9 w-9 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold">C</div>
        <span className="ml-3 font-semibold text-slate-900">Creator SaaS</span>
      </div>
      <nav className="p-3 space-y-1 overflow-y-auto">
        {navDefs.map((def) => {
          const Icon = def.icon;
          const active = activeTabId === def.tabId;
          return (
            <button
              key={def.path}
              type="button"
              onClick={() => handleNav(def)}
              className={`w-full flex items-center px-3 py-2 rounded-lg text-sm transition-colors text-left ${
                active ? "bg-blue-50 text-blue-700" : "text-slate-700 hover:bg-slate-50"
              }`}
            >
              <Icon size={16} />
              <span className="ml-2">{def.label}</span>
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
