import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      colors: {
        // 主题色 — 映射到 CSS 变量，支持运行时切换
        "yc-primary": "var(--color-primary)",
        "yc-primary-hover": "var(--color-primary-hover)",
        "yc-primary-active": "var(--color-primary-active)",
        "yc-primary-bg": "var(--color-primary-bg)",
        "yc-primary-border": "var(--color-primary-border)",

        "yc-bg-base": "var(--color-bg-base)",
        "yc-bg-layout": "var(--color-bg-layout)",
        "yc-bg-sidebar": "var(--color-bg-sidebar)",
        "yc-bg-header": "var(--color-bg-header)",
        "yc-bg-card": "var(--color-bg-card)",
        "yc-bg-secondary": "var(--color-bg-secondary)",
        "yc-bg-tab": "var(--color-bg-tab)",
        "yc-bg-tab-active": "var(--color-bg-tab-active)",
        "yc-bg-code": "var(--color-bg-code)",
        "yc-bg-inset": "var(--color-bg-inset)",

        "yc-text-primary": "var(--color-text-primary)",
        "yc-text-secondary": "var(--color-text-secondary)",
        "yc-text-tertiary": "var(--color-text-tertiary)",
        "yc-text-inverse": "var(--color-text-inverse)",
        "yc-text-link": "var(--color-text-link)",

        "yc-border": "var(--color-border)",
        "yc-border-light": "var(--color-border-light)",

        // 状态色
        "yc-success": "var(--color-success)",
        "yc-success-bg": "var(--color-success-bg)",
        "yc-warning": "var(--color-warning)",
        "yc-warning-bg": "var(--color-warning-bg)",
        "yc-danger": "var(--color-danger)",
        "yc-danger-bg": "var(--color-danger-bg)",
        "yc-info": "var(--color-info)",
        "yc-info-bg": "var(--color-info-bg)",
        "yc-accent": "var(--color-accent)",
        "yc-accent-bg": "var(--color-accent-bg)",

        // 统计指标色
        "yc-stat-positive": "var(--color-stat-positive)",
        "yc-stat-negative": "var(--color-stat-negative)",

        // 选中态/叠加态
        "yc-border-selected": "var(--color-border-selected)",
        "yc-overlay": "var(--color-overlay)",

        // 玻璃态
        "yc-glass-bg": "var(--glass-bg)",
        "yc-glass-border": "var(--glass-border)",

        // 看板专用色
        "yc-bg-column": "var(--color-bg-column)",
        "yc-bg-column-card": "var(--color-bg-column-card)",
        "yc-bg-column-input": "var(--color-bg-column-input)",
        "yc-text-column": "var(--color-text-column)",

        // 图表色
        "yc-chart-1": "var(--color-chart-1)",
        "yc-chart-2": "var(--color-chart-2)",
        "yc-chart-3": "var(--color-chart-3)",
        "yc-chart-4": "var(--color-chart-4)",
        "yc-chart-5": "var(--color-chart-5)",
        "yc-chart-6": "var(--color-chart-6)",
        "yc-chart-7": "var(--color-chart-7)",
        "yc-chart-8": "var(--color-chart-8)",
        "yc-chart-grid": "var(--color-chart-grid)",
        "yc-chart-axis": "var(--color-chart-axis)",
        "yc-chart-tooltip-bg": "var(--color-chart-tooltip-bg)",
        "yc-chart-tooltip-border": "var(--color-chart-tooltip-border)",
        "yc-chart-tooltip-text": "var(--color-chart-tooltip-text)",

        // 渐变色
        "yc-gradient-blue-from": "var(--color-gradient-blue-from)",
        "yc-gradient-blue-to": "var(--color-gradient-blue-to)",
        "yc-gradient-purple-from": "var(--color-gradient-purple-from)",
        "yc-gradient-purple-to": "var(--color-gradient-purple-to)",
        "yc-gradient-green-from": "var(--color-gradient-green-from)",
        "yc-gradient-green-to": "var(--color-gradient-green-to)",
        "yc-gradient-orange-from": "var(--color-gradient-orange-from)",
        "yc-gradient-orange-to": "var(--color-gradient-orange-to)",

        // 卡片变体
        "yc-card-elevated": "var(--color-card-elevated)",
        "yc-card-highlight": "var(--color-card-highlight)",
        "yc-card-stat": "var(--color-card-stat)",
      },
      boxShadow: {
        "yc-sidebar": "var(--shadow-sidebar)",
        "yc-card": "var(--shadow-card)",
      },
      backgroundImage: {
        "yc-gradient-sidebar": "var(--gradient-sidebar)",
        "yc-gradient-header": "var(--gradient-header)",
      },
      backdropBlur: {
        "yc-glass": "var(--glass-blur)",
      },
    },
  },
  plugins: [],
};

export default config;
