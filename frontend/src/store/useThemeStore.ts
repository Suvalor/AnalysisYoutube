import { create } from "zustand";
import { themes, DEFAULT_THEME, type ThemeId } from "@/themes";

const STORAGE_KEY = "yc-theme";

type ThemeState = {
  /** 当前主题 ID */
  themeId: ThemeId;
  /** 切换主题 */
  setTheme: (id: ThemeId) => void;
  /** 从 localStorage 恢复主题（应用启动时调用） */
  initTheme: () => void;
  /** 从后端同步主题（登录后调用） */
  syncFromServer: (serverTheme: string | null | undefined) => void;
};

export const useThemeStore = create<ThemeState>((set) => ({
  themeId: DEFAULT_THEME,

  setTheme: (id: ThemeId) => {
    if (!themes[id]) return;
    set({ themeId: id });
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // localStorage 不可用时静默失败
    }
    // 应用 CSS 变量
    applyThemeTokens(id);
  },

  initTheme: () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && themes[stored as ThemeId]) {
        set({ themeId: stored as ThemeId });
        applyThemeTokens(stored as ThemeId);
        return;
      }
    } catch {
      // ignore
    }
    // 无缓存时使用默认主题
    applyThemeTokens(DEFAULT_THEME);
  },

  syncFromServer: (serverTheme: string | null | undefined) => {
    if (serverTheme && themes[serverTheme as ThemeId]) {
      const id = serverTheme as ThemeId;
      set({ themeId: id });
      try {
        localStorage.setItem(STORAGE_KEY, id);
      } catch {
        // ignore
      }
      applyThemeTokens(id);
    }
  },
}));

/** 将主题 token 应用到 document.documentElement 的 CSS 变量 */
function applyThemeTokens(id: ThemeId) {
  const theme = themes[id];
  if (!theme) return;
  const root = document.documentElement;
  for (const [key, value] of Object.entries(theme.tokens)) {
    root.style.setProperty(key, value);
  }
  // 为 body 设置 data-theme 属性，便于 CSS 选择器
  root.setAttribute("data-theme", id);
}
