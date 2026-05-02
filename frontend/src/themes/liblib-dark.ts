import type { TokenMap } from "./tokens";

/** LibLib 暗色 — 参考 liblib.art，深色背景 + 紫蓝渐变 + 毛玻璃效果 */
export const liblibDarkTokens: TokenMap = {
  "--color-primary": "#a78bfa",
  "--color-primary-hover": "#c4b5fd",
  "--color-primary-active": "#8b5cf6",
  "--color-primary-bg": "rgba(139,92,246,0.15)",
  "--color-primary-border": "rgba(167,139,250,0.3)",

  "--color-bg-base": "#0f0f1a",
  "--color-bg-layout": "#0a0a14",
  "--color-bg-sidebar": "rgba(15,15,30,0.85)",
  "--color-bg-header": "rgba(15,15,30,0.9)",
  "--color-bg-card": "rgba(20,20,40,0.8)",
  "--color-bg-tab": "rgba(20,20,40,0.5)",
  "--color-bg-tab-active": "rgba(25,25,50,0.9)",
  "--color-bg-code": "rgba(30,30,55,0.8)",
  "--color-bg-inset": "rgba(25,25,50,0.6)",

  "--color-text-primary": "#e2e8f0",
  "--color-text-secondary": "#94a3b8",
  "--color-text-tertiary": "#64748b",
  "--color-text-inverse": "#0f0f1a",
  "--color-text-link": "#a78bfa",

  "--color-border": "rgba(139,92,246,0.15)",
  "--color-border-light": "rgba(139,92,246,0.08)",

  "--shadow-sidebar": "4px 0 24px rgba(139,92,246,0.08)",
  "--shadow-card": "0 1px 3px rgba(0,0,0,0.3)",

  "--glass-bg": "rgba(15,15,30,0.75)",
  "--glass-blur": "12px",
  "--glass-border": "rgba(139,92,246,0.12)",

  "--gradient-sidebar": "linear-gradient(180deg, rgba(139,92,246,0.08) 0%, rgba(59,130,246,0.05) 100%)",
  "--gradient-header": "linear-gradient(90deg, rgba(139,92,246,0.06) 0%, rgba(59,130,246,0.04) 100%)",

  // 状态色
  "--color-success": "#52c41a",
  "--color-success-bg": "rgba(82, 196, 26, 0.12)",
  "--color-warning": "#faad14",
  "--color-warning-bg": "rgba(250, 173, 20, 0.12)",
  "--color-danger": "#ff4d4f",
  "--color-danger-bg": "rgba(255, 77, 79, 0.12)",
  "--color-info": "#a78bfa",
  "--color-info-bg": "rgba(167, 139, 250, 0.12)",
  "--color-accent": "#f472b6",
  "--color-accent-bg": "rgba(244, 114, 182, 0.12)",

  // 统计指标色
  "--color-stat-positive": "#4ade80",
  "--color-stat-negative": "#f87171",

  // 选中态/叠加态
  "--color-border-selected": "#a78bfa",
  "--color-overlay": "rgba(0, 0, 0, 0.65)",

  // 看板专用色
  "--color-bg-column": "rgba(20, 20, 40, 0.6)",
  "--color-bg-column-card": "rgba(25, 25, 50, 0.8)",
  "--color-bg-column-input": "rgba(15, 15, 30, 0.8)",
  "--color-text-column": "#94a3b8",

  // 图表色
  "--color-chart-1": "#a78bfa",
  "--color-chart-2": "#4ade80",
  "--color-chart-3": "#facc15",
  "--color-chart-4": "#f87171",
  "--color-chart-5": "#818cf8",
  "--color-chart-6": "#2dd4bf",
  "--color-chart-7": "#f472b6",
  "--color-chart-8": "#fb923c",
  "--color-chart-grid": "rgba(139, 92, 246, 0.08)",
  "--color-chart-axis": "rgba(148, 163, 184, 0.4)",
  "--color-chart-tooltip-bg": "rgba(25, 25, 50, 0.92)",
  "--color-chart-tooltip-border": "rgba(139, 92, 246, 0.3)",
  "--color-chart-tooltip-text": "#e2e8f0",

  // 渐变色
  "--color-gradient-blue-from": "#3b82f6",
  "--color-gradient-blue-to": "#60a5fa",
  "--color-gradient-purple-from": "#8b5cf6",
  "--color-gradient-purple-to": "#a78bfa",
  "--color-gradient-green-from": "#22c55e",
  "--color-gradient-green-to": "#4ade80",
  "--color-gradient-orange-from": "#f97316",
  "--color-gradient-orange-to": "#fb923c",

  // 卡片变体
  "--color-card-elevated": "rgba(25, 25, 50, 0.95)",
  "--color-card-highlight": "rgba(139, 92, 246, 0.08)",
  "--color-card-stat": "rgba(139, 92, 246, 0.05)",
};
