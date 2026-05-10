import type { ThemeConfig } from "antd";

/** Ant Design 5 主题 token 映射 — 每个主题对应一组 antd ConfigProvider theme */
export const antdThemes: Record<string, ThemeConfig> = {
  light: {
    token: {
      colorPrimary: "#1890ff",
      colorBgContainer: "#ffffff",
      colorBgElevated: "#ffffff",
      colorBgLayout: "#f8f9fa",
      colorBorder: "#e2e8f0",
      colorBorderSecondary: "#f1f5f9",
      colorText: "#0f172a",
      colorTextSecondary: "#475569",
      colorTextTertiary: "#94a3b8",
      colorLink: "#1890ff",
      borderRadius: 8,
    },
  },

  "liblib-dark": {
    token: {
      colorPrimary: "#a78bfa",
      colorBgContainer: "rgba(20,20,40,0.8)",
      colorBgElevated: "rgba(25,25,50,0.95)",
      colorBgLayout: "#0a0a14",
      colorBorder: "rgba(139,92,246,0.15)",
      colorBorderSecondary: "rgba(139,92,246,0.08)",
      colorText: "#e2e8f0",
      colorTextSecondary: "#94a3b8",
      colorTextTertiary: "#64748b",
      colorLink: "#a78bfa",
      borderRadius: 8,
    },
    components: {
      Menu: {
        darkItemBg: "transparent",
        darkItemHoverBg: "rgba(139,92,246,0.12)",
        darkItemSelectedBg: "rgba(139,92,246,0.18)",
        darkItemColor: "#94a3b8",
        darkItemHoverColor: "#e2e8f0",
        darkItemSelectedColor: "#a78bfa",
      },
      Input: {
        colorBgContainer: "rgba(20,20,40,0.6)",
        colorBorder: "rgba(139,92,246,0.2)",
        colorTextPlaceholder: "#64748b",
      },
      Select: {
        colorBgContainer: "rgba(20,20,40,0.6)",
        colorBorder: "rgba(139,92,246,0.2)",
        optionSelectedBg: "rgba(139,92,246,0.15)",
      },
      Card: {
        colorBgContainer: "rgba(20,20,40,0.8)",
      },
      Table: {
        colorBgContainer: "rgba(20,20,40,0.6)",
        headerBg: "rgba(25,25,50,0.8)",
        rowHoverBg: "rgba(139,92,246,0.08)",
      },
      Modal: {
        contentBg: "rgba(25,25,50,0.95)",
        headerBg: "rgba(25,25,50,0.95)",
      },
      Tooltip: {
        colorBgSpotlight: "rgba(25,25,50,0.95)",
      },
      Tabs: {
        inkBarColor: "#a78bfa",
        itemActiveColor: "#a78bfa",
        itemSelectedColor: "#a78bfa",
        itemHoverColor: "#c4b5fd",
      },
      Button: {
        defaultBg: "rgba(20,20,40,0.6)",
        defaultBorderColor: "rgba(139,92,246,0.2)",
      },
    },
  },

  "deep-blue": {
    token: {
      colorPrimary: "#22d3ee",
      colorBgContainer: "#122640",
      colorBgElevated: "#152d4a",
      colorBgLayout: "#081422",
      colorBorder: "rgba(34,211,238,0.15)",
      colorBorderSecondary: "rgba(34,211,238,0.08)",
      colorText: "#e0f2fe",
      colorTextSecondary: "#7dd3fc",
      colorTextTertiary: "#38bdf8",
      colorLink: "#22d3ee",
      borderRadius: 8,
    },
    components: {
      Menu: {
        darkItemBg: "transparent",
        darkItemHoverBg: "rgba(34,211,238,0.1)",
        darkItemSelectedBg: "rgba(34,211,238,0.15)",
        darkItemColor: "#7dd3fc",
        darkItemHoverColor: "#e0f2fe",
        darkItemSelectedColor: "#22d3ee",
      },
      Input: {
        colorBgContainer: "#0f1f35",
        colorBorder: "rgba(34,211,238,0.2)",
        colorTextPlaceholder: "#38bdf8",
      },
      Select: {
        colorBgContainer: "#0f1f35",
        colorBorder: "rgba(34,211,238,0.2)",
        optionSelectedBg: "rgba(34,211,238,0.12)",
      },
      Card: {
        colorBgContainer: "#122640",
      },
      Table: {
        colorBgContainer: "#0f1f35",
        headerBg: "#152d4a",
        rowHoverBg: "rgba(34,211,238,0.06)",
      },
      Modal: {
        contentBg: "#152d4a",
        headerBg: "#152d4a",
      },
      Tooltip: {
        colorBgSpotlight: "#152d4a",
      },
      Tabs: {
        inkBarColor: "#22d3ee",
        itemActiveColor: "#22d3ee",
        itemSelectedColor: "#22d3ee",
        itemHoverColor: "#67e8f9",
      },
      Button: {
        defaultBg: "#0f1f35",
        defaultBorderColor: "rgba(34,211,238,0.2)",
      },
    },
  },

  "warm-orange": {
    token: {
      colorPrimary: "#f97316",
      colorBgContainer: "#ffffff",
      colorBgElevated: "#ffffff",
      colorBgLayout: "#fef7f0",
      colorBorder: "#e7e5e4",
      colorBorderSecondary: "#f5f5f4",
      colorText: "#1c1917",
      colorTextSecondary: "#78716c",
      colorTextTertiary: "#a8a29e",
      colorLink: "#f97316",
      borderRadius: 8,
    },
  },
};