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
      },
      boxShadow: {
        "yc-sidebar": "var(--shadow-sidebar)",
        "yc-card": "var(--shadow-card)",
      },
    },
  },
  plugins: [],
};

export default config;
