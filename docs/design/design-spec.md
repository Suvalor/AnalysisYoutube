# 敏感信息接口安全加固 -- 设计规格书

## 1. 设计系统审计结果

### 1.1 审计发现

| 文件 | 问题 | 严重度 |
|------|------|--------|
| `LoginPage.tsx` | email/password Input 无 `autoComplete` | 高 |
| `RegisterPage.tsx` | phone/email/password Input 无 `autoComplete` | 高 |
| `ResetPasswordPage.tsx` | email/password Input 无 `autoComplete` | 高 |
| `authStore.tsx` | `access_token` 存于 `localStorage`，XSS 可窃取 | 高 |
| `apiClient.ts` | 直接从 `localStorage.getItem("access_token")` 读取 | 高 |
| `ConfigCenter.tsx` | 模型表格 Key 列硬编码 `"********"` 无结构化展示 | 中 |

---

## 2. 表单安全属性规范

| 页面 | 字段 | autoComplete | 说明 |
|------|------|--------------|------|
| Login | email | `email` | 引导浏览器填充已保存邮箱 |
| Login | password | `current-password` | 当前站点密码 |
| Login | captcha_code | `off` | 验证码不自动填充 |
| Register | phone | `tel` | 手机号 |
| Register | email | `email` | 邮箱 |
| Register | password | `new-password` | 新密码 |
| Register | confirmPassword | `new-password` | 确认新密码 |
| Register | email_code | `one-time-code` | 验证码 |
| ResetPassword (forgot) | email | `email` | 邮箱 |
| ResetPassword (reset) | new_password | `new-password` | 新密码 |
| ResetPassword (reset) | confirm_password | `new-password` | 确认新密码 |

---

## 3. 密钥脱敏展示交互规格

### 3.1 展示规则

- `has_* === true` 时：显示 `****{last4}` 格式（如 `****a1b2`），等宽字体
- `has_* === false` 时：显示 "未设置"，灰色文字
- 编辑态：`Input.Password`，placeholder="留空不修改"

### 3.2 本次不添加复制按钮

在"最小改动"约束下，脱敏值不可复制为明文。Phase 2 后续可新增 `/me/integration-settings/reveal-secret` 接口（需二次验证）支持复制。

---

## 4. Token 存储方案

### 4.1 本次方案：保持 localStorage 不变

改为 `httpOnly` cookie 属于 L3 级改动，超出本次范围。当前已有 CSP Header 缓解 XSS 风险。

### 4.2 后续建议

- Phase 2: localStorage → sessionStorage（跨Tab失效，但更安全）
- Phase 3: HttpOnly Cookie（需后端改造 + CSRF 防护）

---

## 5. UI 状态矩阵

### 5.1 密钥字段展示

| 状态 | 触发条件 | 展示内容 | 样式 |
|------|----------|----------|------|
| 已配置 | `has_* === true` | `****{last4}` | font-mono, text-primary |
| 未配置 | `has_* === false` | "未设置" | text-tertiary, italic |
| 编辑中 | 点击编辑 | Input.Password | Ant Design 默认 |
| 保存中 | 点击保存 | Input.Password disabled | disabled 态 |

### 5.2 模型表格 Key 列

| 状态 | 触发条件 | 展示内容 |
|------|----------|----------|
| Has Key | `has_api_key === true` | `****{last4}` |
| No Key | `has_api_key === false` | "未设置" |

---
