import { Link } from "react-router-dom";

export default function Dashboard() {
  return (
    <div className="p-6 md:p-10">
      <div className="max-w-4xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
        <h2 className="text-2xl font-semibold mb-3">欢迎来到 Creator SaaS</h2>
        <p className="text-slate-300 mb-6">从左侧导航进入各模块：对标监控、AI 创作、知识库和视频看板。</p>
        <div className="flex flex-wrap gap-3">
          <Link to="/youtube-monitor" className="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-400">
            YouTube 对标监控
          </Link>
          <Link to="/ai-creator" className="px-4 py-2 rounded-lg bg-fuchsia-500 hover:bg-fuchsia-400">
            AI 剧本创作
          </Link>
          <Link to="/video-board" className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400">
            视频看板
          </Link>
        </div>
      </div>
    </div>
  );
}

