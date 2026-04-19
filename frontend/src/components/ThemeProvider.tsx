import { ConfigProvider, theme as antdTheme } from "antd";
import type { ThemeConfig } from "antd";
import zhCN from "antd/locale/zh_CN";
import { useEffect, useMemo, type ReactNode } from "react";
import { themes, isDarkTheme } from "@/themes";
import { useThemeStore } from "@/store/useThemeStore";
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

interface ThemeProviderProps {
  children: ReactNode;
}

export default function ThemeProvider({ children }: ThemeProviderProps) {
  const themeId = useThemeStore((s) => s.themeId);
  const initTheme = useThemeStore((s) => s.initTheme);

  // 启动时初始化主题
  useEffect(() => {
    initTheme();
  }, [initTheme]);

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

  return (
    <ConfigProvider locale={antdZhLocale} theme={antdThemeConfig}>
      {children}
    </ConfigProvider>
  );
}
