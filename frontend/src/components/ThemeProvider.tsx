import { ConfigProvider, theme as antdTheme } from "antd";
import type { ThemeConfig } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import jaJP from "antd/locale/ja_JP";
import koKR from "antd/locale/ko_KR";
import { useEffect, useMemo, type ReactNode } from "react";
import { themes, isDarkTheme } from "@/themes";
import { useThemeStore } from "@/store/useThemeStore";
import { useI18nStore, type Locale } from "@/store/useI18nStore";
import zhCNExtra from "@/locales/zh-CN.json";

/** 合并中文文案：必填校验使用业务文案 */
const antdZhLocale = {
  ...zhCN,
  Form: {
    ...zhCN.Form,
    defaultValidateMessages: {
      ...zhCN.Form?.defaultValidateMessages,
      required: zhCNExtra.required_field_warning,
    },
  },
};

/** Ant Design locale 映射 */
const antdLocaleMap: Record<Locale, typeof zhCN> = {
  "zh-CN": antdZhLocale,
  "en-US": enUS,
  "ja-JP": jaJP,
  "ko-KR": koKR,
};

interface ThemeProviderProps {
  children: ReactNode;
}

export default function ThemeProvider({ children }: ThemeProviderProps) {
  const themeId = useThemeStore((s) => s.themeId);
  const initTheme = useThemeStore((s) => s.initTheme);
  const locale = useI18nStore((s) => s.locale);
  const initLocale = useI18nStore((s) => s.initLocale);

  // 启动时初始化主题和语言
  useEffect(() => {
    initTheme();
    initLocale();
  }, [initTheme, initLocale]);

  // Ant Design 主题配置
  const antdThemeConfig: ThemeConfig | undefined = useMemo(() => {
    const def = themes[themeId];
    if (!def) return undefined;

    const base = def.antdTheme as ThemeConfig;

    // 暗色主题使用 Ant Design 暗色算法
    if (isDarkTheme(themeId)) {
      return {
        ...base,
        algorithm: antdTheme.darkAlgorithm,
      };
    }

    return base;
  }, [themeId]);

  // Ant Design locale
  const antdLocale = antdLocaleMap[locale] ?? antdZhLocale;

  return (
    <ConfigProvider locale={antdLocale} theme={antdThemeConfig}>
      {children}
    </ConfigProvider>
  );
}