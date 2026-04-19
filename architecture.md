# 架构设计文档 — 国际化系统

## 技术栈选型（含理由）

| 技术 | 选型 | 理由 |
|------|------|------|
| i18n 框架 | react-i18next + i18next | React 生态最成熟的 i18n 方案，支持 namespace、插值、复数、懒加载 |
| 语言检测 | i18next-browser-languagedetector | 自动检测浏览器语言，支持 localStorage/cookie/navigator 多策略 |
| 翻译文件 | JSON（按 namespace 分文件） | 轻量、易维护、支持 Git diff、支持 i18next 懒加载 |
| 语言状态 | Zustand store (useI18nStore) | 与项目现有 store 一致，可同步 localStorage + 后端 |
| Ant Design | ConfigProvider locale | 官方推荐方案，切换时动态传入 locale 对象 |
| 后端 | Accept-Language 头 + locale 字段 | REST 标准，后端根据请求头返回对应语言错误消息 |

## 模块结构图

```
frontend/src/
├── i18n/
│   ├── index.ts                    # i18next 初始化配置
│   ├── locales/
│   │   ├── zh-CN/
│   │   │   ├── common.json        # 通用文本（按钮、标签、状态等）
│   │   │   ├── nav.json           # 导航相关
│   │   │   ├── auth.json          # 登录/注册/密码重置
│   │   │   ├── settings.json      # 设置中心/个人设置
│   │   │   ├── radar.json         # 蓝海雷达
│   │   │   ├── youtube.json        # YouTube 相关（频道/视频/竞对）
│   │   │   ├── ai.json            # AI 脚本/智能体
│   │   │   └── sop.json           # SOP 工作流
│   │   ├── en-US/
│   │   │   └── (same structure)
│   │   ├── ja-JP/
│   │   │   └── (same structure)
│   │   └── ko-KR/
│   │       └── (same structure)
│   └── types.ts                    # 翻译 key 类型定义
├── store/
│   └── useI18nStore.ts             # 语言偏好 Zustand store
└── pages/settings/
    └── PersonalSettings.tsx         # 增加语言切换 UI

backend/
├── app/models/user.py              # 新增 locale 字段
├── app/schemas/user.py             # 新增 locale 字段
├── app/api/v1/users.py             # 新增 locale 处理
├── app/core/i18n.py                # 后端消息翻译工具
└── alembic/versions/               # 新增迁移脚本
```

## 数据结构 / API 接口设计

### 翻译文件结构

```json
// locales/zh-CN/common.json
{
  "app": {
    "name": "YouTube Compass",
    "subtitle": "YouTube出海决策工具"
  },
  "action": {
    "save": "保存",
    "cancel": "取消",
    "confirm": "确认",
    "delete": "删除",
    "edit": "编辑",
    "close": "关闭",
    "loading": "加载中...",
    "search": "搜索",
    "reset": "重置"
  },
  "status": {
    "success": "操作成功",
    "error": "操作失败",
    "warning": "警告",
    "noData": "暂无数据"
  }
}
```

### 语言类型定义

```typescript
type Locale = 'zh-CN' | 'en-US' | 'ja-JP' | 'ko-KR';

interface LocaleOption {
  id: Locale;
  name: string;        // 原生语言名（中文、English、日本語、한국어）
  nativeName: string;  // 同 name，用于显示
  flag: string;        // emoji flag
}
```

### 后端 API 变更

**User Settings** — 新增 locale 字段：
```json
{ "locale": "zh-CN" }
```

**Accept-Language 头**：后端读取 `Accept-Language` 请求头，返回对应语言的错误消息。

### 数据库变更

User 表新增字段：
- `locale`: VARCHAR(10), nullable, default NULL（NULL 表示使用默认 zh-CN）

## 文件组织结构

### 新增文件
1. `frontend/src/i18n/index.ts` — i18next 初始化
2. `frontend/src/i18n/types.ts` — 类型定义
3. `frontend/src/i18n/locales/zh-CN/*.json` — 中文翻译（8 个 namespace）
4. `frontend/src/i18n/locales/en-US/*.json` — 英文翻译
5. `frontend/src/i18n/locales/ja-JP/*.json` — 日文翻译
6. `frontend/src/i18n/locales/ko-KR/*.json` — 韩文翻译
7. `frontend/src/store/useI18nStore.ts` — 语言状态管理
8. `backend/app/core/i18n.py` — 后端消息翻译工具
9. `backend/alembic/versions/xxxx_add_locale_to_users.py` — 迁移脚本

### 修改文件
1. `frontend/src/main.tsx` — 挂载 i18n
2. `frontend/src/components/ThemeProvider.tsx` — 同步 Ant Design locale
3. `frontend/src/components/Layout/TabbedShell.tsx` — 翻译导航 + 头像菜单
4. `frontend/src/pages/settings/PersonalSettings.tsx` — 增加语言切换
5. `frontend/src/pages/auth/LoginPage.tsx` — 翻译登录页
6. `frontend/src/pages/auth/RegisterPage.tsx` — 翻译注册页
7. `frontend/src/pages/auth/ResetPasswordPage.tsx` — 翻译密码重置页
8. `frontend/src/pages/settings/ConfigCenter.tsx` — 翻译设置中心
9. `backend/app/models/user.py` — 新增 locale 字段
10. `backend/app/schemas/user.py` — 新增 locale 字段
11. `backend/app/api/v1/users.py` — 新增 locale 处理

## Sprint 规划

### Sprint 1：i18n 基础设施与核心翻译
**范围**：react-i18next 集成 + 语言 Store + 翻译文件结构 + 核心组件翻译 + Ant Design locale 同步
**交付物**：
- i18n/ 目录下所有配置和翻译文件
- useI18nStore.ts
- TabbedShell 翻译
- 登录/注册/密码重置页翻译
- 设置中心/个人设置翻译
- ThemeProvider Ant Design locale 同步

**验收标准**：
- 在个人设置页切换语言后全站核心 UI 文本即时切换
- Ant Design 组件同步切换语言
- 刷新后语言保持

### Sprint 2：业务页面翻译与后端集成
**范围**：业务页面翻译提取 + 后端 locale API + 后端错误消息翻译
**交付物**：
- 蓝海雷达/竞对洞察/频道管理/视频看板等页面翻译
- 后端 locale 字段 + 迁移
- 后端 i18n 工具
- useI18nStore 集成后端 API

**验收标准**：
- 所有业务页面 UI 文本已翻译
- 后端存储语言偏好
- 换设备登录后自动恢复语言

## 风险登记册

| 风险 | 概率 | 影响 | 应对方案 |
|------|------|------|----------|
| 翻译工作量大 | 高 | 中 | 按 namespace 分批翻译，Sprint 1 先覆盖核心 |
| 日韩翻译质量 | 中 | 中 | AI 翻译 + 标注"需校对"，后续迭代优化 |
| 动态文本插值 | 中 | 低 | 统一使用 i18next 插值语法 `{{var}}` |
| Ant Design locale 不完整 | 低 | 低 | 仅覆盖常用组件，冷门组件保留默认 |

## WBS 任务分解

### Sprint 1
1. [T1.1] 安装 react-i18next + i18next + i18next-browser-languagedetector
2. [T1.2] 创建 i18n/index.ts 初始化配置
3. [T1.3] 创建 4 种语言的 common.json 翻译文件
4. [T1.4] 创建 4 种语言的 nav/auth/settings 翻译文件
5. [T1.5] 创建 useI18nStore（Zustand + localStorage 持久化）
6. [T1.6] 更新 main.tsx 挂载 i18n
7. [T1.7] 更新 ThemeProvider 同步 Ant Design locale
8. [T1.8] 翻译 TabbedShell（导航 + 头像菜单 + 标签栏）
9. [T1.9] 翻译登录/注册/密码重置页
10. [T1.10] 翻译设置中心 + 个人设置（含语言切换 UI）

### Sprint 2
11. [T2.1] 创建 radar/youtube/ai/sop namespace 翻译文件
12. [T2.2] 翻译蓝海雷达页面
13. [T2.3] 翻译竞对洞察/频道管理/视频看板页面
14. [T2.4] 翻译 AI 脚本工坊/SOP 工作流页面
15. [T2.5] 后端：User model 新增 locale 字段 + Schema + API
16. [T2.6] 后端：Alembic 迁移脚本
17. [T2.7] 后端：i18n 工具（Accept-Language 解析 + 错误消息翻译）
18. [T2.8] 前端：useI18nStore 集成后端 API