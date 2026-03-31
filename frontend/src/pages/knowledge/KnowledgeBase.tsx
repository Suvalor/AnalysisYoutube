import { Link } from "react-router-dom";

export default function KnowledgeBase() {
  return (
    <div className="p-6 md:p-10">
      <div className="max-w-5xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
        <h2 className="text-xl font-semibold mb-2">知识库管理</h2>
        <p className="text-slate-300 mb-4">可以先通过 API 管理提示词/风格/素材，后续可扩展成完整图形化管理页。</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
            <h3 className="font-medium mb-1">提示词库</h3>
            <p className="text-sm text-slate-400">接口：`/api/libraries/prompts`</p>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
            <h3 className="font-medium mb-1">风格库</h3>
            <p className="text-sm text-slate-400">接口：`/api/libraries/styles`</p>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
            <h3 className="font-medium mb-1">素材库</h3>
            <p className="text-sm text-slate-400">接口：`/api/libraries/assets`</p>
          </div>
        </div>
        <div className="mt-6">
          <Link to="/assets" className="text-emerald-300 hover:text-emerald-200 mr-6">
            前往素材库页面 →
          </Link>
          <Link to="/ai-creator" className="text-indigo-300 hover:text-indigo-200">
            前往 AI 创作工作台 →
          </Link>
        </div>
      </div>
    </div>
  );
}

