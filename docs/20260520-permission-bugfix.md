# 权限系统缺陷修复报告

**日期**：2026-05-20  
**提交**：`91906c6`  
**受影响文件**：`frontend/src/pages/settings/ConfigCenter.tsx`、`frontend/src/components/Layout/TabbedShell.tsx`

---

## 一、缺陷清单

### BUG-01 普通用户拥有管理员级配置权限

**现象**：普通用户（role=user）进入设置中心后，可看到并操作「模型管理」和「云存储与外部API」两个管理员专属 Tab，包括新增/编辑模型库、配置 YouTube API Key、配置云存储凭证等高危操作。

**根因**：

| 位置 | 问题 |
|------|------|
| `TabbedShell.tsx` navDefs | `/config-center` 的 `minRole` 正确设为 `UserRole.USER`（允许普通用户访问，以便管理「智能体」和「风格」）|
| `ConfigCenter.tsx` | 页面内部 **无任何角色检查**，4 个 Tab 对所有已登录用户全量展示 |

**数据核查**：查询 `users` 表确认字段值：

```
id=2  email=suycity@gmail.com          role=admin  ← 管理员账号
id=3  email=whataicompass@126.com      role=user   ← 普通用户账号
```

数据本身无误，问题完全出在前端展示层未做 Tab 级角色过滤。

---

### BUG-02 游客可见所有导航条目，点击后被重定向至登录页

**现象**：未登录用户（guest）浏览时，侧边栏导航虽已根据 `minRole` 正确过滤，但**标签栏（Tab Bar）** 仍残留先前登录会话（管理员/普通用户）打开的标签页。点击这些标签触发 `RequireRole` 重定向至 `/login`。

**根因**：`useTabStore` 为纯内存状态（无 localStorage 持久化）。登出时 `authStore.setToken(null)` 只重置 `role → GUEST`，**未清空** Tab Store。上一个 session 打开的所有标签页依然驻留在标签栏，对游客可见。

---

### BUG-03 管理员专属导航条目对普通用户可见

**现象**：以 `role=user` 身份登录后，若此前以管理员身份打开过「仪表盘」等 `minRole: ADMIN` 的页面，标签栏中仍显示这些条目，点击后重定向至 `/upgrade`。

**根因**：同 BUG-02——Tab Store 未在角色切换时清理，导致高权限标签页「残留」至低权限 session。

---

## 二、修复方案

### Fix-01：ConfigCenter 角色级 Tab 过滤

**文件**：`frontend/src/pages/settings/ConfigCenter.tsx`

```
角色权限矩阵（修复后）：
┌────────────────────┬───────┬──────────┐
│ Tab                │ admin │ user     │
├────────────────────┼───────┼──────────┤
│ 模型管理           │  ✓    │  ✗ 隐藏  │
│ 智能体管理         │  ✓    │  ✓       │
│ 风格管理           │  ✓    │  ✓       │
│ 云存储与外部 API   │  ✓    │  ✗ 隐藏  │
└────────────────────┴───────┴──────────┘
```

变更要点：
1. 引入 `useAuth()` + `hasRole()` 计算 `isAdmin`
2. 初始化 `activeTab` 时，非管理员默认打开 `"prompts"` 而非 `"models"`
3. URL 参数 `?tab=models` / `?tab=integration` 对非管理员静默忽略
4. `role` 变化时（如管理员降权），自动将 activeTab 重置为 `"prompts"`
5. `loadIntegration()` 只在管理员进入 `integration` Tab 时触发
6. `items` 数组通过 `.filter()` 动态移除非管理员不可见的 Tab

### Fix-02 & Fix-03：Tab Store 角色联动清理

**文件**：`frontend/src/components/Layout/TabbedShell.tsx`

**变更 1**：新增 `useEffect([role])` 钩子，在 `role` 变化时扫描 Tab Store：

```typescript
useEffect(() => {
  const { tabs: currentTabs } = useTabStore.getState();
  const unauthorizedTabs = currentTabs.filter((tab) => {
    const minRole = TAB_MIN_ROLE[tab.type];
    return minRole && !hasRole(role, minRole);
  });
  unauthorizedTabs.forEach((tab) => {
    useTabStore.getState().closeTab(tab.id);
  });
  // 若全部标签被清除，导航到当前角色的默认安全页
  if (unauthorizedTabs.length > 0 && unauthorizedTabs.length === currentTabs.length) {
    const defaultPath = hasRole(role, UserRole.USER) ? "/blue-ocean-radar" : "/keyword-research";
    navigate(defaultPath, { replace: true });
  }
}, [role, navigate]);
```

**变更 2**：在 `location.pathname` useEffect 中，`openTab` 前增加角色检查，防止直接输入 URL 向标签栏注入无权限标签：

```typescript
// 修复前
if (def) {
  openTab({ ... });
}

// 修复后
if (def && hasRole(role, def.minRole ?? UserRole.GUEST)) {
  openTab({ ... });
}
```

---

## 三、修复后行为验证

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 普通用户进入设置中心 | 可见全部 4 个 Tab | 仅见「智能体管理」「风格管理」|
| 普通用户访问 `?tab=integration` | 直接跳入集成配置 | 静默忽略，停留在智能体管理 |
| 管理员登出后访问标签栏 | 残留管理员标签可见 | 登出时管理员专属标签自动关闭 |
| 普通用户登出后访问标签栏 | 残留普通用户标签可见 | 登出时 USER 级标签自动关闭 |
| 直接输入 `/dashboard` URL（普通用户）| 标签栏新增 dashboard 标签，点击重定向 | 标签栏不产生 dashboard 标签 |
| 所有标签被清除后 | 空白内容区域，无导航 | 自动导航至角色默认安全页 |

---

## 四、设计决策记录

**为何不在登出时重置整个 Tab Store？**

直接 `useTabStore.setState({ tabs: [], activeTabId: null })` 会一次性清空所有标签（包括游客可访问的 `keyword-research`、`seo-scoring` 等）。现有方案基于角色精确过滤，游客级标签在登出后得以保留，用户体验更平滑。

**为何将清理逻辑放在 `TabbedShell` 而非 `authStore`？**

`authStore` 负责认证状态，不应感知 Tab 结构。将清理逻辑放在 `TabbedShell` 保持关注点分离，且 `TabbedShell` 是唯一持有 `TAB_MIN_ROLE` 映射的地方。
