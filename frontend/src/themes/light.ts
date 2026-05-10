import type { TokenMap } from "./tokens";

/** 浅色经典 — 当前默认风格，slate 灰色系 + 蓝色强调 */
export const lightTokens: TokenMap = {
  "--color-primary": "#1890ff",
  "--color-primary-hover": "#40a9ff",
  "--color-primary-active": "#096dd9",
  "--color-primary-bg": "#e6f4ff",
  "--color-primary-border": "#91caff",

  "--color-bg-base": "#ffffff",
  "--color-bg-secondary": "#f1f5f9",
  "--color-bg-layout": "#f8f9fa",
  "--color-bg-sidebar": "#ffffff",
  "--color-bg-header": "#ffffff",
  "--color-bg-card": "#ffffff",
  "--color-bg-tab": "#f8fafc",
  "--color-bg-tab-active": "#ffffff",
  "--color-bg-code": "#f1f5f9",
  "--color-bg-inset": "#f1f5f9",

  "--color-text-primary": "#0f172a",
  "--color-text-secondary": "#475569",
  "--color-text-tertiary": "#94a3b8",
  "--color-text-inverse": "#ffffff",
  "--color-text-link": "#1890ff",

  "--color-border": "#e2e8f0",
  "--color-border-light": "#f1f5f9",

  "--shadow-sidebar": "4px 0 24px rgba(15,23,42,0.07)",
  "--shadow-card": "0 1px 3px rgba(0,0,0,0.08)",

  "--glass-bg": "transparent",
  "--glass-blur": "0px",
  "--glass-border": "transparent",

  "--gradient-sidebar": "none",
  "--gradient-header": "none",

  // 状态色
  "--color-success": "#52c41a",
  "--color-success-bg": "#f6ffed",
  "--color-warning": "#faad14",
  "--color-warning-bg": "#fffbe6",
  "--color-danger": "#ff4d4f",
  "--color-danger-bg": "#fff2f0",
  "--color-info": "#1890ff",
  "--color-info-bg": "#e6f4ff",
  "--color-accent": "#722ed1",
  "--color-accent-bg": "#f9f0ff",

  // 统计指标色
  "--color-stat-positive": "#52c41a",
  "--color-stat-negative": "#ff4d4f",

  // 选中态/叠加态
  "--color-border-selected": "#1890ff",
  "--color-overlay": "rgba(0, 0, 0, 0.45)",

  // 看板专用色
  "--color-bg-column": "#f8fafc",
  "--color-bg-column-card": "#ffffff",
  "--color-bg-column-input": "#f1f5f9",
  "--color-text-column": "#475569",

  // 图表色
  "--color-chart-1": "#1890ff",
  "--color-chart-2": "#52c41a",
  "--color-chart-3": "#faad14",
  "--color-chart-4": "#ff4d4f",
  "--color-chart-5": "#722ed1",
  "--color-chart-6": "#13c2c2",
  "--color-chart-7": "#eb2f96",
  "--color-chart-8": "#fa8c16",
  "--color-chart-grid": "#f0f0f0",
  "--color-chart-axis": "#8c8c8c",
  "--color-chart-tooltip-bg": "rgba(0, 0, 0, 0.75)",
  "--color-chart-tooltip-border": "rgba(0, 0, 0, 0.9)",
  "--color-chart-tooltip-text": "#ffffff",

  // 渐变色
  "--color-gradient-blue-from": "#1890ff",
  "--color-gradient-blue-to": "#69c0ff",
  "--color-gradient-purple-from": "#722ed1",
  "--color-gradient-purple-to": "#b37feb",
  "--color-gradient-green-from": "#52c41a",
  "--color-gradient-green-to": "#95de64",
  "--color-gradient-orange-from": "#fa8c16",
  "--color-gradient-orange-to": "#ffc069",

  // 卡片变体
  "--color-card-elevated": "#ffffff",
  "--color-card-highlight": "#f0f5ff",
  "--color-card-stat": "#e6f4ff",
};
