import { create } from "zustand";
import i18n from "@/i18n";

const STORAGE_KEY = "yc-locale";

export type Locale = "zh-CN" | "en-US" | "ja-JP" | "ko-KR";

export const LOCALE_OPTIONS: { id: Locale; label: string; flag: string }[] = [
  { id: "zh-CN", label: "中文（简体）", flag: "🇨🇳" },
  { id: "en-US", label: "English", flag: "🇺🇸" },
  { id: "ja-JP", label: "日本語", flag: "🇯🇵" },
  { id: "ko-KR", label: "한국어", flag: "🇰🇷" },
];

export const DEFAULT_LOCALE: Locale = "zh-CN";

interface I18nState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  initLocale: () => void;
  syncFromServer: (serverLocale: string | null | undefined) => void;
}

export const useI18nStore = create<I18nState>((set) => ({
  locale: DEFAULT_LOCALE,

  setLocale: (locale: Locale) => {
    set({ locale });
    i18n.changeLanguage(locale);
    try {
      localStorage.setItem(STORAGE_KEY, locale);
    } catch {
      // ignore
    }
    // 设置 HTML lang 属性
    document.documentElement.lang = locale;
  },

  initLocale: () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && LOCALE_OPTIONS.some((o) => o.id === stored)) {
        set({ locale: stored as Locale });
        i18n.changeLanguage(stored);
        document.documentElement.lang = stored;
        return;
      }
    } catch {
      // ignore
    }
    document.documentElement.lang = DEFAULT_LOCALE;
  },

  syncFromServer: (serverLocale: string | null | undefined) => {
    if (serverLocale && LOCALE_OPTIONS.some((o) => o.id === serverLocale)) {
      const locale = serverLocale as Locale;
      set({ locale });
      i18n.changeLanguage(locale);
      try {
        localStorage.setItem(STORAGE_KEY, locale);
      } catch {
        // ignore
      }
      document.documentElement.lang = locale;
    }
  },
}));