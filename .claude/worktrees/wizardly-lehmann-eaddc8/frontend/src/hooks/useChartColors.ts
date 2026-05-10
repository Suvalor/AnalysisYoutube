import { useMemo } from "react";
import { useThemeStore } from "@/store/useThemeStore";

/** 从 CSS 变量读取颜色值 */
function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** 图表颜色集合 */
export interface ChartColors {
  /** 系列色数组 (8 色) */
  series: string[];
  /** 网格线颜色 */
  grid: string;
  /** 坐标轴颜色 */
  axis: string;
  /** 提示框样式 */
  tooltip: {
    bg: string;
    border: string;
    text: string;
  };
  /** 渐变色对 */
  gradient: {
    blue: [string, string];
    purple: [string, string];
    green: [string, string];
    orange: [string, string];
  };
}

/** 图表色 CSS 变量前缀 */
const CHART_SERIES_VARS = [
  "--color-chart-1",
  "--color-chart-2",
  "--color-chart-3",
  "--color-chart-4",
  "--color-chart-5",
  "--color-chart-6",
  "--color-chart-7",
  "--color-chart-8",
] as const;

/** 获取当前主题的图表颜色，themeId 变化时自动刷新 */
export function useChartColors(): ChartColors {
  const themeId = useThemeStore((s) => s.themeId);

  return useMemo<ChartColors>(() => {
    const series = CHART_SERIES_VARS.map((v) => getCSSVar(v));

    // 防御性回退：如果所有 series 颜色均为空（CSS 变量未加载或已过期），使用硬编码 fallback
    const FALLBACK_SERIES = [
      "#5470C6", "#91CC75", "#FAC858", "#EE6666",
      "#73C0DE", "#3BA272", "#FC8452", "#9A60B4",
    ];
    const resolvedSeries = series.every((c) => c === "") ? FALLBACK_SERIES : series;

    const gradient: ChartColors["gradient"] = {
      blue: [getCSSVar("--color-gradient-blue-from"), getCSSVar("--color-gradient-blue-to")],
      purple: [getCSSVar("--color-gradient-purple-from"), getCSSVar("--color-gradient-purple-to")],
      green: [getCSSVar("--color-gradient-green-from"), getCSSVar("--color-gradient-green-to")],
      orange: [getCSSVar("--color-gradient-orange-from"), getCSSVar("--color-gradient-orange-to")],
    };

    return {
      series: resolvedSeries,
      grid: getCSSVar("--color-chart-grid"),
      axis: getCSSVar("--color-chart-axis"),
      tooltip: {
        bg: getCSSVar("--color-chart-tooltip-bg"),
        border: getCSSVar("--color-chart-tooltip-border"),
        text: getCSSVar("--color-chart-tooltip-text"),
      },
      gradient,
    };
  }, [themeId]);
}
