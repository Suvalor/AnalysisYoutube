import { Home, BarChart3, WandSparkles, Library, Kanban, Youtube, LogOut, Menu as MenuIcon, Image } from "lucide-react";
import { ReactNode, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/store/authStore";

type AppLayoutProps = {
  children: ReactNode;
};

const navItems = [
  { key: "/dashboard", label: "仪表盘", icon: Home },
  { key: "/youtube-monitor", label: "YouTube 对标监控", icon: Youtube },
  { key: "/ai-creator", label: "AI 剧本创作", icon: WandSparkles },
  { key: "/knowledge-base", label: "知识库管理", icon: Library },
  { key: "/assets", label: "素材库", icon: Image },
  { key: "/video-board", label: "视频看板", icon: Kanban },
  { key: "/competitor-analysis", label: "对标图表", icon: BarChart3 },
];

function titleByPath(pathname: string) {
  const found = navItems.find((item) => pathname.startsWith(item.key));
  return found?.label ?? "Creator SaaS";
}

export default function AppLayout({ children }: AppLayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { setToken } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const pageTitle = useMemo(() => titleByPath(location.pathname), [location.pathname]);

  const logout = () => {
    setToken(null);
    navigate("/login");
  };

  const SidebarContent = (
    <aside className="h-full bg-slate-900 border-r border-slate-800 flex flex-col">
      <div className="h-16 px-4 flex items-center border-b border-slate-800">
        <div className="h-9 w-9 rounded-lg bg-indigo-500 text-white flex items-center justify-center font-bold">C</div>
        <span className="ml-3 font-semibold text-slate-100">Creator SaaS</span>
      </div>
      <nav className="p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = location.pathname.startsWith(item.key);
          return (
            <Link
              key={item.key}
              to={item.key}
              onClick={() => setMobileOpen(false)}
              className={`flex items-center px-3 py-2 rounded-lg text-sm transition-colors ${
                active ? "bg-indigo-500/20 text-indigo-300" : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              <Icon size={16} />
              <span className="ml-2">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <div className="hidden lg:block w-72 shrink-0">{SidebarContent}</div>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur px-4 md:px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-md hover:bg-slate-800"
              aria-label="打开侧边栏"
            >
              <MenuIcon size={18} />
            </button>
            <h1 className="text-base md:text-lg font-semibold">{pageTitle}</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-slate-700 flex items-center justify-center text-sm">U</div>
            <button onClick={logout} className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-sm flex items-center">
              <LogOut size={14} className="mr-1.5" />
              登出
            </button>
          </div>
        </header>
        <main className="flex-1 min-h-0">{children}</main>
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

