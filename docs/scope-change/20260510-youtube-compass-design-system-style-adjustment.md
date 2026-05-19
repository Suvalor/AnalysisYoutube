# YouTube Compass Design System 样式调整需求文档

**日期**：2026-05-10
**状态**：已完成
**优先级**：P1 — 已完成
**技能**：默认

## 背景

本地已新增 `youtube-compass-design-system` 样式能力。当前需要基于该设计系统，对 YouTube Compass 前端界面进行统一样式调整，使核心业务页面在视觉语言、组件状态、间距密度和交互反馈上保持一致。

本文档只定义需求与验收标准，不直接约束具体实现文件。实现阶段应优先复用现有 React、Ant Design、Tailwind CSS 和项目内已有布局结构，避免为了样式调整重写业务逻辑。

## 目标

1. 统一全站基础视觉风格，确保新增设计系统样式成为前端 UI 的主要样式基线。
2. 保持 YouTube Compass 工具型产品的工作台气质：清晰、克制、信息密度合理、适合反复使用。
3. 降低不同模块之间的视觉割裂感，尤其是表格、卡片、表单、按钮、标签、弹窗、侧边栏和顶部标签栏。
4. 在不改变核心业务流程的前提下，提升页面可读性、层级感和交互反馈。

## 适用范围

优先覆盖以下前端区域：

- 全局布局：`TabbedShell`、侧边栏、顶部标签栏、内容区容器。
- 核心分析页面：蓝海雷达、趋势发现、关键词研究、频道增长、频道管理。
- 配置与管理页面：设置中心、智能体管理、集成配置。
- 通用组件状态：按钮、输入框、选择器、表格、卡片、标签、统计指标、空状态、加载状态、错误状态、确认弹窗。

暂不要求覆盖：

- 登录、注册、找回密码页面的品牌化重设计。
- 业务字段、接口协议、权限逻辑、数据缓存逻辑变更。
- 大规模组件库重构。

## 设计原则

### 1. 工具优先

界面应服务于数据扫描、筛选、对比和决策。避免营销式大标题、过度装饰、大片渐变背景或低信息密度卡片堆叠。

### 2. 层级清晰

页面应形成稳定层级：

- 页面级标题和操作区清晰分离。
- 查询条件区与结果区视觉边界明确。
- 结果区内表格、列表、趋势卡片和统计数据的主次关系明确。

### 3. 组件一致

相同语义的组件应有一致外观和交互：

- 主操作按钮统一高亮样式。
- 次要操作、危险操作、文本操作有明确区分。
- 可点击行、可排序列、可入库按钮、跳转按钮应有一致 hover 和 focus 反馈。

### 4. 信息密度合理

该产品偏工作台，不应过度放大字号或间距。桌面端应优先支持批量浏览和快速比较；移动端应保证关键操作不拥挤、不溢出。

## 样式调整需求

### 全局布局

- 侧边栏导航需要统一选中态、hover 态、折叠态和图标颜色。
- 顶部标签栏需要统一当前标签、普通标签、关闭按钮、溢出标签的状态样式。
- 主内容区应有稳定的页面内边距和最大宽度策略，避免不同页面左右边距不一致。
- 页面背景、分割线、卡片边框、阴影层级需要统一，不允许不同模块各自使用明显冲突的颜色和阴影。

### 卡片与区块

- 查询条件区、历史记录区、结果统计区、列表结果区应使用一致的容器样式。
- 卡片圆角建议保持克制，除非 `youtube-compass-design-system` 已定义更具体的 token。
- 卡片内标题、说明、操作按钮和内容区域的间距应统一。
- 不允许出现卡片套卡片造成的视觉噪音；确有分组需求时优先使用分割线、标题或轻量背景区分。

### 表格与列表

- 表头、排序态、hover 行、选中行、可点击行需要统一。
- 数字字段应保持可扫描性，播放量、点赞、评论、订阅、互动率等指标应右对齐或采用一致的数字排版。
- 趋势发现的「趋势视频排行」需要继续保留可排序视觉反馈。
- 无限滚动列表需要有明确的加载中、已加载全部、空数据和错误状态。

### 表单与筛选区

- 输入框、选择器、日期选择、搜索按钮、重置按钮需统一高度和间距。
- 查询条件区的主按钮应明显，但不能压过结果内容。
- 表单校验错误态、禁用态、加载态需要符合设计系统样式。

### 按钮与操作

- 主按钮用于「获取趋势」「开始分析」「保存」等主要动作。
- 次按钮用于「重置」「取消」「查看」等辅助动作。
- 危险按钮用于删除、解绑、清空等高风险动作。
- 「入库」类按钮需要与主题色匹配并高亮，但不能与主查询按钮混淆。
- 图标按钮必须有 hover、focus 和 disabled 状态。

### 颜色与主题

- 使用 `youtube-compass-design-system` 的色彩 token 作为优先来源。
- 全局主色、成功色、警告色、错误色、信息色需要语义一致。
- 避免单一色系铺满全站；数据页面需要足够的中性色层级承载信息。
- 深色文字、次级文字、占位文字、禁用文字需要有清晰层级。

### 字体与间距

- 页面标题、区块标题、表头、正文、辅助说明、数字指标应有统一字号层级。
- 不使用随视口宽度变化的字体大小。
- 字间距保持默认，不使用负字距。
- 工具型页面的垂直间距应紧凑但不拥挤。

### 交互反馈

- 所有可点击元素必须有明确 hover 态。
- 键盘 focus 态不能被移除，应符合可访问性要求。
- 加载状态要标明当前阻塞点，例如按钮 loading、区块 skeleton、列表底部 loading。
- 异常状态需要提供清晰错误提示和可恢复动作。

## 页面级验收标准

### 趋势发现

- 查询条件区、最近查询、趋势视频排行三个区域视觉层级清晰。
- 最近查询历史记录样式紧凑，可区分当前选择项。
- 趋势视频排行支持无限滚动，同时保留播放量、赞、评论、互动率、频道订阅排序态。
- 视频行可点击打开 YouTube，操作按钮与行点击不冲突。
- 「入库」按钮样式高亮且与频道管理联动语义明确。

### 关键词研究

- 分析条件、历史记录、热门视频区域样式一致。
- 热门视频无限滚动的加载态、空态、结束态清晰。
- 从频道增长跳转带入关键词时，输入框状态和分析结果区域不产生视觉突兀。

### 频道增长

- Channel Overview 的表格或列表需要强化关键字可操作性。
- 关键词录入到关键词研究的操作入口应清晰但不过度抢占主操作。
- 数据概览卡片的数字排版、趋势标识和辅助说明保持统一。

### 设置中心与智能体管理

- 标签页、表单、编辑弹窗、模型配置卡片样式统一。
- 编辑智能体页面与设置中心之间的导航状态清晰，不出现视觉闪烁或标签状态混乱。
- API Key、Base URL 等敏感配置字段应有明确的输入态、保存态和错误提示。

## 非功能要求

- 不改变现有 API 协议。
- 不改变现有数据库结构。
- 不改变现有权限和组织隔离逻辑。
- 不引入新的全局状态管理方案。
- 不破坏 Ant Design 组件的可访问性默认行为。
- 样式调整后需要通过前端构建或 TypeScript 检查；若存在历史遗留错误，需要在交付说明中区分新旧问题。

## 验收清单

- 全站核心页面使用统一的设计系统 token 或等价变量。
- 主内容区、卡片、表格、表单、按钮、标签、弹窗视觉一致。
- 趋势发现、关键词研究、频道增长、设置中心页面没有明显样式割裂。
- 所有新增或调整的交互元素都有 hover、focus、disabled、loading 状态。
- 桌面端 1440px、移动端 390px 宽度下无文字溢出、按钮挤压、内容重叠。
- 趋势视频排行排序功能保留。
- 无限滚动列表在加载中、空数据、加载完成时都有明确反馈。
- 不出现大面积单一色系、过度圆角、卡片套卡片、营销式 hero 布局。

## 实施建议

1. 先确认 `youtube-compass-design-system` 的 token 入口、全局样式入口和组件覆盖方式。
2. 优先调整全局布局、基础组件和共享样式变量。
3. 再按页面处理趋势发现、关键词研究、频道增长、设置中心。
4. 每完成一个页面，做桌面端和移动端截图验收。
5. 最后统一检查颜色、间距、字号、交互状态和构建结果。

## 实施结果（2026-05-10）

### 已完成

- 全局布局（Layout.tsx）：侧边栏、顶部栏、用户头像区全部迁移到 `yc-` 前缀 Tailwind 类和 CSS 变量
- 核心分析页面：趋势发现（TrendDiscovery）、关键词研究（KeywordResearch）、频道增长（ChannelGrowthDashboard）、仪表盘（Dashboard）全部完成迁移
- 配置与管理页面：AI 模型设置（AiModelSettings）、智能体编辑（AgentEditorPage）、SEO 评分（SeoScoring）全部完成迁移
- 其他页面：AI 脚本工坊（AICreator）、飞书文档（FeishuDocList/FeishuDocViewer）、知识库（KnowledgeBase）、素材库（AssetLibrary）、SOP（ScriptWorkflowSOP）、下载列表（DownloadList）、灵感池（InspirationPool）、YouTube 配额仪表盘（YouTubeQuotaDashboard）全部完成迁移
- 通用组件：MixConfigModal、MarkdownEditorToggle、ScriptPreview 完成迁移
- 设计系统补充：新增 `--color-bg-secondary` token 及对应 Tailwind `yc-bg-secondary` 类，覆盖全部 4 个主题
- 前端构建验证通过（`npm run build` 成功）

### 保留项（不迁移）

- 登录/注册/找回密码页面（AuthLayout、LoginPage、RegisterPage、ResetPasswordPage）：按需求文档明确排除
- AssetLibrary 深色主题 slate 类（`bg-slate-900/80`、`border-slate-800` 等）：设计系统无暗色主题 token，强制迁移会破坏视觉意图
- BlueOceanRadar 打印导出模板中的内联十六进制颜色：`window.document.write` 生成独立 HTML，CSS 变量在目标窗口不可用

### 变更文件清单（29 files）

- `frontend/src/components/Layout/Layout.tsx` — 侧边栏/顶部栏全面迁移
- `frontend/src/components/Layout/AuthLayout.tsx` — 微调
- `frontend/src/components/MarkdownEditorToggle.tsx` — 样式迁移
- `frontend/src/components/MixConfigModal.tsx` — 样式迁移
- `frontend/src/components/ScriptPreview.tsx` — 样式迁移
- `frontend/src/pages/ai/AICreator.tsx` — 样式迁移
- `frontend/src/pages/dashboard/Dashboard.tsx` — 样式迁移
- `frontend/src/pages/feishu/FeishuDocList.tsx` — 样式迁移
- `frontend/src/pages/feishu/FeishuDocViewer.tsx` — 样式迁移
- `frontend/src/pages/growth/ChannelGrowthDashboard.tsx` — 样式迁移
- `frontend/src/pages/inspiration/InspirationPool.tsx` — 样式迁移
- `frontend/src/pages/keyword/KeywordResearch.tsx` — 样式迁移
- `frontend/src/pages/knowledge/AssetLibrary.tsx` — accentColor + 文字颜色迁移
- `frontend/src/pages/knowledge/KnowledgeBase.tsx` — 样式迁移
- `frontend/src/pages/seo/SeoScoring.tsx` — 样式迁移
- `frontend/src/pages/settings/AgentEditorPage.tsx` — 样式迁移
- `frontend/src/pages/settings/AiModelSettings.tsx` — 样式迁移
- `frontend/src/pages/sop/ScriptWorkflowSOP.tsx` — 样式迁移
- `frontend/src/pages/trend/TrendDiscovery.tsx` — 样式迁移
- `frontend/src/pages/youtube/DownloadList.tsx` — 样式迁移
- `frontend/src/pages/youtube/YouTubeQuotaDashboard.tsx` — 样式迁移
- `frontend/src/styles/index.css` — 新增 `--color-bg-secondary` 变量
- `frontend/src/themes/tokens.ts` — 新增 `BG_SECONDARY` token
- `frontend/src/themes/light.ts` — 新增 `--color-bg-secondary`
- `frontend/src/themes/deep-blue.ts` — 新增 `--color-bg-secondary`
- `frontend/src/themes/liblib-dark.ts` — 新增 `--color-bg-secondary`
- `frontend/src/themes/warm-orange.ts` — 新增 `--color-bg-secondary`
- `frontend/tailwind.config.ts` — 新增 `yc-bg-secondary` 映射
- `frontend/package-lock.json` — npm 依赖重装（rollup 平台修复）

## 风险与注意事项

- 如果直接覆盖 Ant Design 全局样式，可能影响弹窗、表单校验、表格排序等默认行为，需要逐项验证。
- 如果设计系统样式与 Tailwind 工具类同时作用于同一元素，可能出现优先级冲突。
- 如果只调整页面局部样式，不抽取共享 token 或公共类，后续页面容易再次割裂。
- 样式变更应避免影响已有业务逻辑，尤其是趋势发现、关键词研究和频道管理之间的联动。
