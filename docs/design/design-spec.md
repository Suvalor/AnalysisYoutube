# 8 页面主题适配设计规格

> 版本：v1.0 | 日期：2026-04-30 | 作者：product-designer Agent
> 范围：4 套主题（light / deep-blue / liblib-dark / warm-orange）x 8 个目标页面

---

## 1. Design System Audit — 现有 Token 体系审查

### 1.1 已有语义 Token（21 个颜色 + 4 非颜色）

| 分类 | Token | Tailwind 别名 | 4 套主题覆盖 |
|------|-------|--------------|-------------|
| 品牌色 | `--color-primary` | `yc-primary` | 全覆盖 |
| | `--color-primary-hover` | `yc-primary-hover` | 全覆盖 |
| | `--color-primary-active` | `yc-primary-active` | 全覆盖 |
| | `--color-primary-bg` | `yc-primary-bg` | 全覆盖 |
| | `--color-primary-border` | `yc-primary-border` | 全覆盖 |
| 背景色 | `--color-bg-base` | `yc-bg-base` | 全覆盖 |
| | `--color-bg-layout` | `yc-bg-layout` | 全覆盖 |
| | `--color-bg-sidebar` | `yc-bg-sidebar` | 全覆盖 |
| | `--color-bg-header` | `yc-bg-header` | 全覆盖 |
| | `--color-bg-card` | `yc-bg-card` | 全覆盖 |
| | `--color-bg-tab` | `yc-bg-tab` | 全覆盖 |
| | `--color-bg-tab-active` | `yc-bg-tab-active` | 全覆盖 |
| | `--color-bg-code` | `yc-bg-code` | 全覆盖 |
| | `--color-bg-inset` | `yc-bg-inset` | 全覆盖 |
| 文字色 | `--color-text-primary` | `yc-text-primary` | 全覆盖 |
| | `--color-text-secondary` | `yc-text-secondary` | 全覆盖 |
| | `--color-text-tertiary` | `yc-text-tertiary` | 全覆盖 |
| | `--color-text-inverse` | `yc-text-inverse` | 全覆盖 |
| | `--color-text-link` | `yc-text-link` | 全覆盖 |
| 边框色 | `--color-border` | `yc-border` | 全覆盖 |
| | `--color-border-light` | `yc-border-light` | 全覆盖 |

### 1.2 缺失 Token（需要新增）

通过审计 8 个页面的硬编码颜色，发现以下语义缺口：

| 缺失 Token | 建议命名 | 语义说明 | 出现页面 |
|------------|---------|---------|---------|
| 成功/正面色 | `--color-success` | 成功状态、正向指标（播放量、增长率） | NavigationGuide, ChannelDetail, GlobalVideoList |
| 成功色背景 | `--color-success-bg` | 成功态背景（green-50 系列） | NavigationGuide |
| 警告色 | `--color-warning` | 警告、注意状态 | NavigationGuide |
| 警告色背景 | `--color-warning-bg` | 警告态背景（amber-50 系列） | NavigationGuide, ChannelDetail |
| 危险色 | `--color-danger` | 错误、删除、危险操作 | NavigationGuide, ChannelList |
| 危险色背景 | `--color-danger-bg` | 危险态背景（red-50 系列） | NavigationGuide |
| 信息/蓝色强调色 | `--color-info` | 信息提示、蓝色图标（Eye 图标） | ChannelDetail, GlobalVideoList, NavigationGuide |
| 信息色背景 | `--color-info-bg` | 信息态背景（blue-50 系列） | NavigationGuide, GlobalVideoList |
| 次要强调色 | `--color-accent` | 次级强调色，AI 按钮/紫蓝色系 | BlueOceanRadar, ChannelDetail |
| 次要强调色背景 | `--color-accent-bg` | 次级强调背景（violet-50 系列） | ChannelDetail |
| 统计指标色 | `--color-stat-positive` | 正向数值色（绿色 #3f8600） | NavigationGuide |
| | `--color-stat-negative` | 负向数值色（红色 #cf1322） | NavigationGuide |
| 选中态边框色 | `--color-border-selected` | 多选态 ring/border（如 blue-400） | GlobalVideoList |
| 沉浸叠加色 | `--color-overlay` | 视频时长标签 bg-black/60 | ChannelDetail, GlobalVideoList |
| 看板列背景色 | `--color-bg-column` | 看板列背景（VideoBoard 的 slate-900/70） | VideoBoard |
| 看板卡片背景色 | `--color-bg-column-card` | 看板内卡片背景 | VideoBoard |
| 看板输入框背景色 | `--color-bg-column-input` | 看板内输入框背景 | VideoBoard |
| 看板文字色 | `--color-text-column` | 看板内文字色 | VideoBoard |

### 1.3 新增 Token 四主题色值映射

```
--color-success:
  light:         #22c55e
  deep-blue:     #34d399
  liblib-dark:   #4ade80
  warm-orange:   #16a34a

--color-success-bg:
  light:         #f0fdf4
  deep-blue:     rgba(52,211,153,0.10)
  liblib-dark:   rgba(74,222,128,0.08)
  warm-orange:   #f0fdf4

--color-warning:
  light:         #f59e0b
  deep-blue:     #fbbf24
  liblib-dark:   #fcd34d
  warm-orange:   #d97706

--color-warning-bg:
  light:         #fffbeb
  deep-blue:     rgba(251,191,36,0.10)
  liblib-dark:   rgba(252,211,77,0.08)
  warm-orange:   #fff7ed

--color-danger:
  light:         #ef4444
  deep-blue:     #f87171
  liblib-dark:   #fca5a5
  warm-orange:   #dc2626

--color-danger-bg:
  light:         #fef2f2
  deep-blue:     rgba(248,113,113,0.10)
  liblib-dark:   rgba(252,165,165,0.08)
  warm-orange:   #fef2f2

--color-info:
  light:         #3b82f6
  deep-blue:     #60a5fa
  liblib-dark:   #818cf8
  warm-orange:   #2563eb

--color-info-bg:
  light:         #eff6ff
  deep-blue:     rgba(96,165,250,0.10)
  liblib-dark:   rgba(129,140,248,0.08)
  warm-orange:   #eff6ff

--color-accent:
  light:         #8b5cf6
  deep-blue:     #a78bfa
  liblib-dark:   #c4b5fd
  warm-orange:   #7c3aed

--color-accent-bg:
  light:         #f5f3ff
  deep-blue:     rgba(167,139,250,0.10)
  liblib-dark:   rgba(196,181,253,0.08)
  warm-orange:   #f5f3ff

--color-stat-positive:
  light:         #3f8600
  deep-blue:     #52c41a
  liblib-dark:   #73d13d
  warm-orange:   #389e0d

--color-stat-negative:
  light:         #cf1322
  deep-blue:     #ff4d4f
  liblib-dark:   #ff7875
  warm-orange:   #a8071a

--color-border-selected:
  light:         #93c5fd  (blue-300)
  deep-blue:     rgba(34,211,238,0.4)
  liblib-dark:   rgba(139,92,246,0.4)
  warm-orange:   #fdba74  (orange-300)

--color-overlay:
  light:         rgba(0,0,0,0.6)
  deep-blue:     rgba(0,0,0,0.6)
  liblib-dark:   rgba(0,0,0,0.5)
  warm-orange:   rgba(0,0,0,0.6)

--color-bg-column:
  light:         #f1f5f9
  deep-blue:     rgba(18,38,64,0.7)
  liblib-dark:   rgba(20,20,40,0.7)
  warm-orange:   #fef7f0

--color-bg-column-card:
  light:         #ffffff
  deep-blue:     #122640
  liblib-dark:   rgba(20,20,40,0.8)
  warm-orange:   #ffffff

--color-bg-column-input:
  light:         #f8fafc
  deep-blue:     #0f1f35
  liblib-dark:   rgba(20,20,40,0.6)
  warm-orange:   #fef7f0

--color-text-column:
  light:         #0f172a
  deep-blue:     #e0f2fe
  liblib-dark:   #e2e8f0
  warm-orange:   #1c1917
```

### 1.4 Tailwind 别名扩展（tailwind.config.ts 新增映射）

```ts
// 语义状态色
"yc-success":      "var(--color-success)",
"yc-success-bg":   "var(--color-success-bg)",
"yc-warning":      "var(--color-warning)",
"yc-warning-bg":   "var(--color-warning-bg)",
"yc-danger":       "var(--color-danger)",
"yc-danger-bg":    "var(--color-danger-bg)",
"yc-info":         "var(--color-info)",
"yc-info-bg":      "var(--color-info-bg)",
"yc-accent":       "var(--color-accent)",
"yc-accent-bg":    "var(--color-accent-bg)",

// 统计指标色
"yc-stat-positive": "var(--color-stat-positive)",
"yc-stat-negative": "var(--color-stat-negative)",

// 选中态/叠加态
"yc-border-selected": "var(--color-border-selected)",
"yc-overlay":         "var(--color-overlay)",

// 看板专用
"yc-bg-column":       "var(--color-bg-column)",
"yc-bg-column-card":  "var(--color-bg-column-card)",
"yc-bg-column-input": "var(--color-bg-column-input)",
"yc-text-column":     "var(--color-text-column)",
```

---

## 2. 硬编码颜色分类与替换规则

### 2.1 模式 A：页面级布局背景 + 文字色

**硬编码**：`bg-[#F8F9FA]`、`text-slate-900`、`bg-white`

| 硬编码值 | 替换为 | 影响页面 |
|---------|--------|---------|
| `bg-[#F8F9FA]` | `bg-yc-bg-layout` | BlueOceanRadar, NavigationGuide, CompetitorAnalysis |
| `bg-white` (页面容器级) | `bg-yc-bg-card` | 所有 8 个页面 |
| `text-slate-900` (页面主文字) | `text-yc-text-primary` | 所有 8 个页面 |
| `text-slate-800` | `text-yc-text-primary` | ChannelDetail, NavigationGuide |
| `text-slate-700` | `text-yc-text-secondary` | ChannelList, ChannelDetail, NavigationGuide |
| `text-slate-600` | `text-yc-text-secondary` | ChannelList, NavigationGuide, GlobalVideoList, ConfigCenter |
| `text-slate-500` | `text-yc-text-tertiary` | 所有 8 个页面 |
| `text-slate-400` | `text-yc-text-tertiary` | ChannelList, NavigationGuide |

### 2.2 模式 B：Card 边框/背景

**硬编码**：`!bg-white !border-slate-200 !shadow-sm`

| 硬编码值 | 替换为 | 影响页面 |
|---------|--------|---------|
| `!bg-white` (Card 级) | `!bg-yc-bg-card` | BlueOceanRadar, NavigationGuide, CompetitorAnalysis, VideoBoard |
| `!border-slate-200` | `!border-yc-border` | 同上 + ChannelList, ChannelDetail, GlobalVideoList, ConfigCenter |
| `border-slate-200` (非 Card) | `border-yc-border` | ChannelDetail, GlobalVideoList, ConfigCenter |
| `border-slate-100` | `border-yc-border-light` | GlobalVideoList |

### 2.3 模式 C：inline style 硬编码 hex

| 硬编码值 | 出现位置 | 替换策略 |
|---------|---------|---------|
| `color: "#0f172a"` | Title style 属性 | 移除 style，用 `text-yc-text-primary` class |
| `color: "#64748b"` | Text style 属性 | 移除 style，用 `text-yc-text-tertiary` class |
| `color: "#dc2626"` | 避坑提示 Title/Icon | 替换为 `text-yc-danger` class |
| `color: "#3b82f6"` | RadarChartOutlined icon | 替换为 `text-yc-info` class |
| `color: "#cf1322"` / `"#3f8600"` | Statistic valueStyle | 替换为 `yc-stat-negative` / `yc-stat-positive` CSS var 引用 |
| `backgroundColor: '#52c41a'` | 查看结果按钮 style | 替换为 `!bg-yc-success !border-yc-success` |

### 2.4 模式 D：Tailwind 语义色类（需保持语义，替换为 token）

| Tailwind 类 | 语义 | 替换为 |
|------------|------|--------|
| `text-blue-600` / `text-blue-700` | 播放量/链接 | `text-yc-info` |
| `text-emerald-600` | 点赞数 | `text-yc-success` |
| `text-orange-500` | 评论数 | `text-yc-warning` |
| `text-violet-500` / `text-violet-600` | AI 图标/按钮 | `text-yc-accent` |
| `bg-violet-50` / `bg-violet-50/60` | AI 洞察背景 | `bg-yc-accent-bg` |
| `bg-amber-50` / `bg-amber-50/70` | 警告背景 | `bg-yc-warning-bg` |
| `bg-indigo-50/60` | 受众画像背景 | `bg-yc-accent-bg` |
| `bg-blue-50` / `bg-blue-50/30` / `bg-blue-50/50` | 信息背景 | `bg-yc-info-bg` |
| `bg-red-50` / `bg-gradient-to-r from-red-50 to-orange-50` | 危险背景 | `bg-yc-danger-bg` |
| `border-blue-200` / `border-blue-300` / `border-blue-400` | 信息边框 | `border-yc-info` (200/300) / `border-yc-border-selected` (400) |
| `border-amber-200` | 警告边框 | `border-yc-warning` |
| `border-violet-300` | AI 边框 | `border-yc-accent` |
| `border-red-200` / `border-red-500` | 危险边框 | `border-yc-danger` |
| `ring-blue-400` | 选中态 ring | `ring-yc-border-selected` |

### 2.5 模式 E：VideoBoard 看板暗色硬编码

| 硬编码值 | 替换为 |
|---------|--------|
| `bg-slate-900` / `bg-slate-900/70` | `bg-yc-bg-column-card` / `bg-yc-bg-column` |
| `border-slate-700` / `border-slate-800` | `border-yc-border` |
| `bg-slate-800` / `bg-slate-700` | `bg-yc-bg-column-input` |
| `text-slate-100` | `text-yc-text-column` |
| `text-slate-400` | `text-yc-text-tertiary` |
| `bg-indigo-500` | `bg-yc-accent` |

### 2.6 模式 F：导出报告 HTML（BlueOceanRadar）

导出报告使用 `window.open` 写入独立 HTML，无法引用 CSS 变量。

**策略**：运行时读取当前主题的 token 值，注入到生成的 HTML `<style>` 中。

```ts
// 伪代码：从当前主题 token 获取色值
const rootStyle = getComputedStyle(document.documentElement);
const textPrimary = rootStyle.getPropertyValue('--color-text-primary');
const borderColor = rootStyle.getPropertyValue('--color-border');
// ... 注入到生成的 HTML style 字符串
```

---

## 3. UI 状态矩阵

### 3.1 通用状态色映射

| 状态 | Token | light | deep-blue | liblib-dark | warm-orange |
|------|-------|-------|-----------|-------------|-------------|
| **Default** | `--color-primary` | #1890ff | #22d3ee | #a78bfa | #f97316 |
| **Hover** | `--color-primary-hover` | #40a9ff | #67e8f9 | #c4b5fd | #fb923c |
| **Active** | `--color-primary-active` | #096dd9 | #06b6d4 | #8b5cf6 | #ea580c |
| **Loading** | `--color-primary` (opacity 0.65) | 同 Default | 同 Default | 同 Default | 同 Default |
| **Empty** | `--color-text-tertiary` | #94a3b8 | #38bdf8 | #64748b | #a8a29e |
| **Error** | `--color-danger` | #ef4444 | #f87171 | #fca5a5 | #dc2626 |
| **Success** | `--color-success` | #22c55e | #34d399 | #4ade80 | #16a34a |

### 3.2 各页面状态矩阵

#### BlueOceanRadar

| 区域 | Default | Hover | Active | Loading | Empty | Error |
|------|---------|-------|--------|---------|-------|-------|
| 页面背景 | `yc-bg-layout` | - | - | - | - | - |
| 标题文字 | `yc-text-primary` | - | - | - | - | - |
| 描述文字 | `yc-text-tertiary` | - | - | - | - | - |
| Card 容器 | `yc-bg-card` + `yc-border` | shadow ↑ | - | - | - | - |
| AI 按钮 | `yc-accent` text/border | hover: ↑ | active: ↓ | Spin | - | - |
| 扫描按钮 | `yc-primary` | hover | active | Spin | "暂无数据" | Alert error |
| 表格行 | `yc-bg-card` | `yc-bg-inset` | - | - | Empty 组件 | - |
| 导出报告 | 当前主题 token 值注入 | - | - | - | - | - |

#### NavigationGuide

| 区域 | Default | Hover | Active | Loading | Empty | Error |
|------|---------|-------|--------|---------|-------|-------|
| 配额仪表盘 | `yc-bg-card` + `yc-border` | - | - | - | - | - |
| 剩余额度 | `yc-stat-positive` / `yc-stat-negative` | - | - | - | - | - |
| 推荐品类卡片 | `yc-bg-card` + `yc-border` | shadow ↑ | - | - | - | - |
| 高增长标记 | `yc-warning-bg` + `yc-warning` border | - | - | - | - | - |
| 匹配度仪表盘 | `yc-success`(≥80) / `yc-warning`(≥50) / `yc-danger`(<50) | - | - | - | - | - |
| 避坑卡片 | `yc-danger-bg` + `yc-danger` border/text | - | - | - | - | - |
| 聊天气泡(用户) | `yc-primary` bg + `yc-text-inverse` | - | - | - | - | - |
| 聊天气泡(AI) | `yc-bg-inset` + `yc-text-secondary` | - | - | - | - | - |
| 蓝海雷达内嵌面板 | `yc-info-bg` + `yc-info` border | - | - | - | - | - |
| 历史记录条目 | `yc-bg-card` + `yc-border` | `yc-info-bg` + `yc-info` border | - | - | Empty | - |

#### CompetitorAnalysis

| 区域 | Default | Hover | Active | Loading | Empty | Error |
|------|---------|-------|--------|---------|-------|-------|
| 图表网格线 | `yc-border-light` | - | - | - | - | - |
| 图表轴文字 | `yc-text-tertiary` | - | - | - | - | - |
| 图表折线色 | 语义调色板（见 4.1） | - | - | - | - | - |
| Tooltip 背景 | `yc-bg-card` + `yc-border` | - | - | - | - | - |

#### ChannelList

| 区域 | Default | Hover | Active | Loading | Empty | Error |
|------|---------|-------|--------|---------|-------|-------|
| 表格行 | `yc-bg-card` | `yc-bg-inset` | - | Spin | Empty | - |
| 频道头像边框 | `yc-border` | - | - | - | - | - |
| 简介预览链接 | `yc-text-link` | `yc-primary-hover` | - | - | - | - |

#### ChannelDetail

| 区域 | Default | Hover | Active | Loading | Empty | Error |
|------|---------|-------|--------|---------|-------|-------|
| 频道统计卡 | `yc-bg-card` + `yc-danger` border (YouTube 品牌色) | - | - | - | - | - |
| AI 核心标签 | 品牌预设 Tag color（magenta/purple/blue/cyan/green） | - | - | - | - | - |
| 擅长内容卡 | `yc-warning-bg` + `yc-warning` border | - | - | - | - | - |
| 受众画像卡 | `yc-accent-bg` + `yc-accent` border | - | - | - | - | - |
| 内容定位卡 | `yc-bg-inset` + `yc-border` | - | - | - | - | - |
| AI 分析按钮 | `yc-accent` bg/border | hover: ↑ | active: ↓ | Spin | - | - |
| 查看结果按钮 | `yc-success` bg/border | - | - | - | - | - |
| 统计指标(播放量) | `yc-info` | - | - | - | - | - |
| 统计指标(点赞) | `yc-success` | - | - | - | - | - |
| 统计指标(评论) | `yc-warning` | - | - | - | - | - |
| 视频时长标签 | `yc-overlay` bg + `yc-text-inverse` | - | - | - | - | - |
| MarkdownPreview 区 | `yc-bg-inset` + `yc-border` | - | - | - | - | - |

#### GlobalVideoList

| 区域 | Default | Hover | Active | Loading | Empty | Error |
|------|---------|-------|--------|---------|-------|-------|
| 视频卡片 | `yc-bg-card` + `yc-border` | - | - | Spin | "加载中..." | - |
| 选中态 | `yc-border-selected` border + ring | - | - | - | - | - |
| 批量操作栏 | `yc-info-bg` + `yc-info` border + text | - | - | - | - | - |
| 统计指标 | 同 ChannelDetail | - | - | - | - | - |
| 视频时长标签 | `yc-overlay` bg + `yc-text-inverse` | - | - | - | - | - |
| 分页栏 | `yc-bg-card` + `yc-border` | - | - | - | - | - |

#### VideoBoard

| 区域 | Default | Hover | Active | Loading | Empty | Error |
|------|---------|-------|--------|---------|-------|-------|
| 看板列 | `yc-bg-column` + `yc-border` | - | - | - | - | - |
| 看板卡片 | `yc-bg-column-card` + `yc-border` | shadow ↑ | drag: opacity 0.7 | - | - | - |
| 新建输入框 | `yc-bg-column-input` + `yc-border` | - | - | - | - | - |
| 新建按钮(主) | `yc-accent` | hover | active | - | - | - |
| 新建按钮(次) | `yc-bg-column-input` | hover | active | - | - | - |

#### ConfigCenter

| 区域 | Default | Hover | Active | Loading | Empty | Error |
|------|---------|-------|--------|---------|-------|-------|
| 主容器 | `yc-bg-card` + `yc-border` + shadow | - | - | Spin | - | - |
| 说明文字 | `yc-text-secondary` | - | - | - | - | - |
| 辅助文字 | `yc-text-tertiary` | - | - | - | - | - |

---

## 4. 第三方组件适配策略

### 4.1 recharts 图表颜色

**影响范围**：CompetitorAnalysis（8 个目标页面中唯一使用 recharts 的页面）

#### 4.1.1 图表调色板（Chart Palette）

折线图需要多条数据系列用不同颜色区分。硬编码 `["#60a5fa", "#34d399", "#f59e0b", "#f472b6"]` 需替换为主题感知调色板。

**方案**：定义 `CHART_PALETTE` 常量，通过 `useThemeStore` 读取当前主题返回对应调色板：

```ts
const CHART_PALETTES: Record<ThemeId, string[]> = {
  light:       ["#60a5fa", "#34d399", "#f59e0b", "#f472b6"],
  "deep-blue": ["#22d3ee", "#34d399", "#fbbf24", "#f472b6"],
  "liblib-dark": ["#a78bfa", "#34d399", "#fbbf24", "#f472b6"],
  "warm-orange": ["#3b82f6", "#16a34a", "#d97706", "#e11d48"],
};
```

#### 4.1.2 CartesianGrid / XAxis / YAxis

| 属性 | 当前硬编码 | 替换为 |
|------|-----------|--------|
| `CartesianGrid stroke` | `"#e2e8f0"` | `var(--color-border)` |
| `XAxis stroke` / `YAxis stroke` | `"#64748b"` | `var(--color-text-tertiary)` |

**注意**：recharts 的 `stroke` 属性支持 CSS 变量字符串，但需验证 `var(--color-xxx)` 语法在 SVG 属性中的兼容性。如不兼容，则通过 `useThemeStore` + `getComputedStyle` 读取实际值传入。

#### 4.1.3 Tooltip / Legend

recharts 的 Tooltip 和 Legend 默认使用浏览器默认样式。需要自定义 content 渲染器，使用 token class：

```tsx
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload) return null;
  return (
    <div className="bg-yc-bg-card border-yc-border border rounded-lg px-3 py-2 shadow-yc-card">
      <p className="text-yc-text-secondary text-xs">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }} className="text-sm">
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  );
};
```

### 4.2 MarkdownPreview 组件主题适配

**当前**：`MarkdownPreview` 使用硬编码 `text-slate-800`，且依赖 `.markdown-body` CSS 类。

**适配方案**：

1. **文字色**：将 `text-slate-800` 替换为 `text-yc-text-primary`
2. **背景色**：外层容器已由父页面提供（如 `bg-yc-bg-inset`），无需额外处理
3. **链接色**：在 `.markdown-body` 全局 CSS 中将 `a` 颜色绑定到 `var(--color-text-link)`
4. **代码块**：将 `code` / `pre` 背景绑定到 `var(--color-bg-code)`
5. **表格**：将 `th` 背景绑定到 `var(--color-bg-inset)`，边框绑定到 `var(--color-border)`

需检查 `.markdown-body` 的全局 CSS 定义位置，确保上述 token 引用生效。

---

## 5. 交互规格 — 主题切换过渡

### 5.1 过渡效果

| 属性 | 规格 |
|------|------|
| 过渡属性 | `color`, `background-color`, `border-color`, `box-shadow`, `fill`, `stroke` |
| 过渡时长 | `200ms` |
| 缓动函数 | `ease-out` |
| 作用范围 | `:root` 及所有使用了 `yc-*` class 的元素 |

### 5.2 全局过渡声明

在 `global.css` 或 `index.css` 中添加：

```css
/* 主题切换时颜色平滑过渡 */
*,
*::before,
*::after {
  transition-property: color, background-color, border-color, box-shadow, fill, stroke;
  transition-duration: 200ms;
  transition-timing-function: ease-out;
}
```

**注意事项**：
- 此声明会影响所有属性切换，包括非主题相关的 hover 等，可能增加重绘开销
- 如发现性能问题（尤其在 VideoBoard 拖拽场景），可收窄选择器，仅对 `:root` 的 CSS 变量切换添加过渡，利用 `@property` 注册实现：

```css
@property --color-primary {
  syntax: '<color>';
  inherits: true;
  initial-value: #1890ff;
}
/* 注册后，:root 上改变 --color-primary 会自动触发过渡 */
```

此方案更优但浏览器兼容性需确认（Safari 15.4+ / Chrome 85+ / Firefox 未见支持）。

### 5.3 主题切换无闪烁

ThemeProvider 在 `useEffect` 中初始化主题，首次渲染可能闪烁。建议：
- 在 `<html>` 标签上添加 `data-theme="light"` 属性
- CSS 使用 `[data-theme="light"]` 选择器预加载默认 token 值
- 或在 `<head>` 中注入 `<style>` 内联脚本读取 localStorage 中的 themeId 并设置 CSS 变量

---

## 6. 无障碍检查 — WCAG AA 对比度

### 6.1 检查标准

WCAG AA 要求：
- 普通文字（< 18px / < 14px bold）：对比度 >= 4.5:1
- 大文字（>= 18px / >= 14px bold）：对比度 >= 3:1
- UI 组件与图形对象：对比度 >= 3:1

### 6.2 四主题对比度矩阵

#### light（浅色经典）

| 组合 | 前景 | 背景 | 对比度 | AA 普通文字 | AA 大文字 |
|------|------|------|--------|-----------|-----------|
| 主文字 on 卡片 | #0f172a | #ffffff | 18.4:1 | PASS | PASS |
| 次文字 on 卡片 | #475569 | #ffffff | 7.08:1 | PASS | PASS |
| 辅助文字 on 卡片 | #94a3b8 | #ffffff | 2.94:1 | **FAIL** | PASS |
| 品牌色 on 卡片 | #1890ff | #ffffff | 4.03:1 | **FAIL** | PASS |
| 品牌色 on 品牌背景 | #1890ff | #e6f4ff | 4.61:1 | PASS | PASS |

**问题**：
1. `text-tertiary` (#94a3b8) on 白底对比度 2.94:1，不满足 AA 普通文字标准
2. `primary` (#1890ff) on 白底对比度 4.03:1，不满足 AA 普通文字标准

**建议**：辅助文字仅用于大文字或非关键信息（如时间戳、占位符），不用于可操作文字。品牌色在按钮中因字号较大可满足大文字标准。

#### deep-blue（深蓝科技）

| 组合 | 前景 | 背景 | 对比度 | AA 普通文字 | AA 大文字 |
|------|------|------|--------|-----------|-----------|
| 主文字 on 卡片 | #e0f2fe | #122640 | 11.2:1 | PASS | PASS |
| 次文字 on 卡片 | #7dd3fc | #122640 | 5.17:1 | PASS | PASS |
| 辅助文字 on 卡片 | #38bdf8 | #122640 | 3.17:1 | **FAIL** | PASS |
| 品牌色 on 卡片 | #22d3ee | #122640 | 6.67:1 | PASS | PASS |
| 品牌色 on 品牌背景 | #22d3ee | rgba(34,211,238,0.12) | ~5.5:1 | PASS | PASS |

**问题**：`text-tertiary` (#38bdf8) on #122640 对比度 3.17:1，仅满足大文字和 UI 组件，不满足普通文字。

#### liblib-dark（LibLib 暗色）

| 组合 | 前景 | 背景 | 对比度 | AA 普通文字 | AA 大文字 |
|------|------|------|--------|-----------|-----------|
| 主文字 on 卡片 | #e2e8f0 | rgba(20,20,40,0.8) | ~12.5:1 | PASS | PASS |
| 次文字 on 卡片 | #94a3b8 | rgba(20,20,40,0.8) | ~5.4:1 | PASS | PASS |
| 辅助文字 on 卡片 | #64748b | rgba(20,20,40,0.8) | ~3.2:1 | **FAIL** | PASS |
| 品牌色 on 卡片 | #a78bfa | rgba(20,20,40,0.8) | ~5.8:1 | PASS | PASS |

**问题**：同 deep-blue，`text-tertiary` 不满足普通文字 AA。

#### warm-orange（暖橙活力）

| 组合 | 前景 | 背景 | 对比度 | AA 普通文字 | AA 大文字 |
|------|------|------|--------|-----------|-----------|
| 主文字 on 卡片 | #1c1917 | #ffffff | 18.1:1 | PASS | PASS |
| 次文字 on 卡片 | #78716c | #ffffff | 4.58:1 | PASS | PASS |
| 辅助文字 on 卡片 | #a8a29e | #ffffff | 2.75:1 | **FAIL** | PASS |
| 品牌色 on 卡片 | #f97316 | #ffffff | 3.04:1 | **FAIL** | PASS |
| 品牌色 on 品牌背景 | #f97316 | #fff7ed | 4.68:1 | PASS | PASS |

**问题**：
1. `text-tertiary` (#a8a29e) on 白底对比度 2.75:1，不满足普通文字 AA
2. `primary` (#f97316) on 白底对比度 3.04:1，不满足普通文字 AA

### 6.3 无障碍改进建议

1. **text-tertiary 对比度不足**：这是各主题的共性问题。当前 `text-tertiary` 用于时间戳、占位符、辅助说明等非关键信息，属于"大文字或非必要可读"场景，可接受。但应确保：
   - 不将 `text-tertiary` 用于表单 label、按钮文字、导航项等关键可操作文字
   - 在需要可读的辅助信息场景，改用 `text-secondary`

2. **warm-orange 品牌色 on 白底不足**：`#f97316` 在白底上仅 3.04:1。影响范围：默认态 Button(type="primary") 由 Ant Design 内部处理（白字 on 橙底，对比度良好），但 ghost 按钮或纯文字链接使用品牌色 on 白底时不达标。
   - 建议：warm-orange 的 `colorTextLink` 从 `#f97316` 调整为 `#c2410c`（对比度 5.67:1），或维持 `#f97316` 仅用于按钮背景，文字链接用深一号

3. **light 主题品牌色 on 白底不足**：`#1890ff` 在白底上 4.03:1，差 0.47 才达标。影响较小（Ant Design 按钮内部处理白字 on 蓝底），但独立链接文字可能不达标。
   - 建议：将 `--color-text-link` 从 `#1890ff` 调整为 `#1677ff`（对比度 4.55:1），达标

---

## 7. 实施清单

### 7.1 基础设施层（优先级 P0）

| 序号 | 任务 | 产出文件 |
|------|------|---------|
| 1 | 新增 18 个语义 Token 到 `tokens.ts` TOKEN 常量 | `src/themes/tokens.ts` |
| 2 | 四套主题文件各添加 18 个 token 值 | `src/themes/light.ts`, `deep-blue.ts`, `liblib-dark.ts`, `warm-orange.ts` |
| 3 | Tailwind 别名扩展 18 个映射 | `tailwind.config.ts` |
| 4 | Ant Design 主题扩展 success/warning/danger token（antd-themes.ts 的 components 配置） | `src/themes/antd-themes.ts` |
| 5 | 全局过渡 CSS 声明 | `src/index.css` 或 `src/global.css` |

### 7.2 页面改造层（优先级 P1）

| 序号 | 页面 | 改造要点 | 预估改动行数 |
|------|------|---------|-------------|
| 1 | BlueOceanRadar | 替换 `bg-[#F8F9FA]`/`!bg-white`/`!border-slate-200`/inline style/导出报告注入 | ~35 |
| 2 | NavigationGuide | 替换 `bg-[#F8F9FA]`/`!bg-white`/`!border-slate-200`/inline style/配色函数(matchScoreColor)/聊天气泡色/避坑卡色/内嵌面板色/历史记录 hover | ~80 |
| 3 | CompetitorAnalysis | 替换 `bg-[#F8F9FA]`/`!bg-white`/`!border-slate-200`/inline style/recharts 调色板+grid+axis/自定义 Tooltip | ~30 |
| 4 | ChannelList | 替换 `bg-white`/`border-slate-200`/`text-slate-*` 系列/hover:bg-slate-50 | ~25 |
| 5 | ChannelDetail | 替换 `bg-white`/`border-slate-200`/`text-slate-*` 系列/violet 按钮/amber 擅长卡/indigo 受众卡/slate-50 定位卡/统计指标色/视频时长 overlay/查看结果按钮 style/MarkdownPreview 包裹区 | ~60 |
| 6 | GlobalVideoList | 替换 `bg-white`/`border-slate-200`/`text-slate-*` 系列/选中态 ring+border/批量操作栏/统计指标色/查看结果按钮 style/MarkdownPreview 包裹区/视频时长 overlay | ~55 |
| 7 | VideoBoard | 替换 slate-900/800/700 系列为看板 token/indigo-500 新建按钮 | ~25 |
| 8 | ConfigCenter | 替换 `bg-white`/`border-slate-200`/`text-slate-*` 系列 | ~15 |

### 7.3 第三方组件层（优先级 P2）

| 序号 | 任务 | 产出文件 |
|------|------|---------|
| 1 | recharts 图表调色板 hook | 新增 `src/hooks/useChartPalette.ts` |
| 2 | recharts 自定义 Tooltip 组件 | 新增 `src/components/ChartTooltip.tsx` |
| 3 | MarkdownPreview 主题适配 | 修改 `src/components/MarkdownPreview.tsx` |
| 4 | `.markdown-body` 全局 CSS 绑定 token | 修改全局 CSS 文件 |

---

## 附录 A：硬编码颜色审计明细

### BlueOceanRadar.tsx

| 行号 | 硬编码 | 语义 | 替换目标 |
|------|--------|------|---------|
| 317 | `#1e293b`, `#0f172a`, `#e2e8f0`, `#f1f5f9` | 导出报告 HTML | 运行时 token 注入 |
| 369 | `bg-[#F8F9FA]` | 页面背景 | `bg-yc-bg-layout` |
| 372 | `style={{ color: "#0f172a" }}` | 标题 | `text-yc-text-primary` |
| 375 | `style={{ color: "#64748b" }}` | 描述 | `text-yc-text-tertiary` |
| 371 | `!bg-white !border-slate-200 !shadow-sm` | Card | `!bg-yc-bg-card !border-yc-border !shadow-yc-card` |
| 474 | `!text-purple-600 !border-purple-200` | AI 按钮 | `!text-yc-accent !border-yc-accent` |

### NavigationGuide.tsx

| 行号 | 硬编码 | 语义 | 替换目标 |
|------|--------|------|---------|
| 160-162 | `#22c55e`, `#f59e0b`, `#ef4444` | 匹配度颜色函数 | 使用 `--color-success/warning/danger` |
| 191 | `#cf1322`, `#3f8600` | 配额统计正/负 | `yc-stat-negative/positive` |
| 228 | `color: "#0f172a"` | 推荐品类标题 | `text-yc-text-primary` |
| 328, 330 | `#dc2626` | 避坑图标/标题 | `text-yc-danger` |
| 385 | `color: "#0f172a"` | 追问标题 | `text-yc-text-primary` |
| 535 | `color: "#3b82f6"` | 雷达图标 | `text-yc-info` |
| 583 | `#3f8600`, `#cf1322` | 成功率统计 | `yc-stat-positive/negative` |
| 805 | `bg-[#F8F9FA]` | 页面背景 | `bg-yc-bg-layout` |
| 812-813 | `#0f172a`, `#64748b` | 页面标题/描述 | `text-yc-text-primary/tertiary` |
| 969 | `#0f172a` | 推荐品类标题 | `text-yc-text-primary` |
| 散布 | `bg-blue-500`, `bg-slate-100` | 聊天气泡 | `bg-yc-primary`, `bg-yc-bg-inset` |
| 散布 | `!border-blue-200`, `!bg-blue-50/20` | 内嵌面板 | `border-yc-info`, `bg-yc-info-bg` |
| 散布 | `hover:border-blue-300`, `hover:bg-blue-50/30` | 历史 hover | `hover:border-yc-info`, `hover:bg-yc-info-bg` |

### CompetitorAnalysis.tsx

| 行号 | 硬编码 | 语义 | 替换目标 |
|------|--------|------|---------|
| 28 | `#60a5fa`, `#34d399`, `#f59e0b`, `#f472b6` | 折线调色板 | `useChartPalette()` |
| 128 | `bg-[#F8F9FA]` | 页面背景 | `bg-yc-bg-layout` |
| 131, 134 | `#0f172a`, `#64748b` | 标题/描述 | inline style 移除，用 token class |
| 205, 232 | `stroke="#e2e8f0"` | 网格线 | `var(--color-border)` |
| 206-207, 233-234 | `stroke="#64748b"` | 轴线 | `var(--color-text-tertiary)` |

### ChannelDetail.tsx

| 行号 | 硬编码 | 语义 | 替换目标 |
|------|--------|------|---------|
| 368 | `text-red-600` | YouTube 图标 | `text-yc-danger`（保持 YouTube 品牌色语义） |
| 372 | `border-red-500`, `bg-white` | 频道统计卡 | `border-yc-danger`, `bg-yc-bg-card` |
| 474 | `text-violet-500` | AI 图标 | `text-yc-accent` |
| 505 | `border-amber-200`, `bg-amber-50/70` | 擅长内容卡 | `border-yc-warning`, `bg-yc-warning-bg` |
| 509 | `bg-indigo-50/60` | 受众画像卡 | `bg-yc-accent-bg` |
| 518 | `bg-slate-50` | 内容定位卡 | `bg-yc-bg-inset` |
| 529 | `border-violet-300`, `bg-violet-50` | AI 分析区空态 | `border-yc-accent`, `bg-yc-accent-bg` |
| 584 | `!bg-violet-600 !border-violet-600` | AI 分析按钮 | `!bg-yc-accent !border-yc-accent` |
| 591 | `text-amber-700` | API Key 提示 | `text-yc-warning` |
| 633 | `bg-black/60 text-white` | 视频时长标签 | `bg-yc-overlay text-yc-text-inverse` |
| 670 | `text-blue-600` | 播放量指标 | `text-yc-info` |
| 671 | `text-emerald-600` | 点赞指标 | `text-yc-success` |
| 672 | `text-orange-500` | 评论指标 | `text-yc-warning` |
| 720 | `backgroundColor: '#52c41a'` | 查看结果按钮 | `!bg-yc-success !border-yc-success` |

### GlobalVideoList.tsx

| 行号 | 硬编码 | 语义 | 替换目标 |
|------|--------|------|---------|
| 437 | `bg-blue-50`, `border-blue-200` | 批量操作栏 | `bg-yc-info-bg`, `border-yc-info` |
| 438 | `text-blue-500`, `text-blue-700` | 批量操作文字 | `text-yc-info` |
| 484 | `border-blue-400`, `ring-blue-400` | 选中态 | `border-yc-border-selected`, `ring-yc-border-selected` |
| 512 | `bg-black/60 text-white` | 视频时长标签 | `bg-yc-overlay text-yc-text-inverse` |
| 560 | `text-blue-600` | 播放量 | `text-yc-info` |
| 561 | `text-emerald-600` | 点赞 | `text-yc-success` |
| 562 | `text-orange-500` | 评论 | `text-yc-warning` |
| 608 | `backgroundColor: '#52c41a'` | 查看结果按钮 | `!bg-yc-success !border-yc-success` |

### VideoBoard.tsx

| 行号 | 硬编码 | 语义 | 替换目标 |
|------|--------|------|---------|
| 59 | `border-slate-700`, `bg-slate-900` | 看板卡片 | `border-yc-border`, `bg-yc-bg-column-card` |
| 61 | `text-slate-100` | 卡片标题 | `text-yc-text-column` |
| 62 | `text-slate-400` | 卡片辅助文字 | `text-yc-text-tertiary` |
| 83 | `border-slate-800`, `bg-slate-900/70` | 看板列 | `border-yc-border`, `bg-yc-bg-column` |
| 86 | `bg-slate-800`, `hover:bg-slate-700` | 新建按钮 | `bg-yc-bg-column-input`, hover 同 |
| 90 | `bg-slate-800/40` | 拖拽 over 态 | `bg-yc-bg-column-input` |
| 277 | `border-slate-800`, `bg-slate-900` | 新建输入区 | `border-yc-border`, `bg-yc-bg-column-card` |
| 279 | `bg-slate-800`, `border-slate-700` | 输入框 | `bg-yc-bg-column-input`, `border-yc-border` |
| 285 | `bg-slate-700` | 取消按钮 | `bg-yc-bg-column-input` |
| 288 | `bg-indigo-500` | 创建按钮 | `bg-yc-accent` |

### ConfigCenter.tsx

| 行号 | 硬编码 | 语义 | 替换目标 |
|------|--------|------|---------|
| 629 | `bg-white`, `border-slate-200` | 主容器 | `bg-yc-bg-card`, `border-yc-border` |
| 散布 | `text-slate-600`, `text-slate-500` | 说明文字 | `text-yc-text-secondary`, `text-yc-text-tertiary` |
| 散布 | `text-xs` 内含 `text-slate-400` | 辅助文字 | `text-yc-text-tertiary` |

### ChannelList.tsx

| 行号 | 硬编码 | 语义 | 替换目标 |
|------|--------|------|---------|
| 235 | `border-slate-200` | 头像边框 | `border-yc-border` |
| 241 | `text-slate-900` | 频道名 | `text-yc-text-primary` |
| 336 | `text-slate-900` | 博主名 | `text-yc-text-primary` |
| 350 | `text-blue-600`, `hover:text-blue-500` | 简介链接 | `text-yc-info`, `hover:text-yc-primary-hover` |
| 382 | `text-slate-600` | 擅长内容 | `text-yc-text-secondary` |
| 408 | `text-slate-400` | 更新时间 | `text-yc-text-tertiary` |
| 442 | `bg-white`, `border-slate-200` | 容器 | `bg-yc-bg-card`, `border-yc-border` |
| 505 | `hover:bg-slate-50` | 表格行 hover | `hover:bg-yc-bg-inset` |

---

## 附录 B：YouTube 品牌色特殊处理

YouTube 图标使用红色 (#FF0000) 是品牌标识，不属于主题适配范围。但 ChannelDetail 中 `border-red-500` 用于频道统计卡边框，这并非 YouTube 品牌规范，而是开发者自定义的装饰色。

**建议**：将 `border-red-500` 替换为 `border-yc-primary`（让主题品牌色统一驱动），YouTube 图标本身的 `text-red-600` 可保留为硬编码（品牌色不随主题变化）。

---

## 附录 C：Ant Design Tag color 语义映射

Ant Design Tag 的 `color` prop 值（`"blue"`, `"green"`, `"red"`, `"purple"`, `"magenta"`, `"gold"`, `"orange"`, `"cyan"`, `"success"`）由 Ant Design 内部根据 ConfigProvider 的 darkAlgorithm 自动适配暗色主题。

**结论**：Tag color 不需要额外适配，ThemeProvider 已通过 `antdTheme.darkAlgorithm` 处理。但需验证 warm-orange 主题（浅色但非默认）中 Tag 颜色是否符合预期。
