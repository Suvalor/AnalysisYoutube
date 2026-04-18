# 架构设计文档 — 完善登录注册功能

## 技术栈选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 图形验证码 | Pillow + io.BytesIO | 轻量级，后端生成图片，无需前端依赖 |
| 邮件发送 | aiosmtplib + Jinja2 | 异步SMTP，项目已有SMTP配置基础 |
| 验证码存储 | Redis 或 内存dict | 验证码短生命周期，无需持久化 |
| 密码重置Token | 现有 JWT 机制 | 复用 create_access_token，设置短有效期 |
| 前端表单 | Ant Design Form + Input | 现有技术栈 |

## 模块结构图

```
前端:
  LoginPage.tsx ── 增加验证码+记住账号+忘记密码链接
  RegisterPage.tsx ── 重构: 手机号+邮箱+验证码
  ResetPasswordPage.tsx ── 新增: 重置密码页面

后端:
  /api/auth/captcha ── GET 获取图形验证码
  /api/auth/login ── POST 登录(增加验证码校验)
  /api/auth/register ── POST 注册(手机号+邮箱+验证码)
  /api/auth/send-email-code ── POST 发送邮箱验证码
  /api/auth/forgot-password ── POST 忘记密码(发送重置链接)
  /api/auth/reset-password ── POST 重置密码(验证token+设新密码)
```

## 数据结构 / API 接口设计

### User Model 扩展

```python
# 新增字段
phone = Column(String(20), unique=True, nullable=True, comment="手机号")
email_verified = Column(Boolean, default=False, comment="邮箱是否已验证")
```

### 新增 Schema

```python
class CaptchaResponse(BaseModel):
    captcha_id: str      # 验证码ID
    captcha_image: str    # Base64编码的图片

class RegisterRequest(BaseModel):
    phone: str            # 手机号
    password: str         # 密码
    email: str            # 邮箱
    email_code: str       # 邮箱验证码

class SendEmailCodeRequest(BaseModel):
    email: str            # 邮箱地址

class ForgotPasswordRequest(BaseModel):
    phone: str            # 手机号(用于查找关联邮箱)

class ResetPasswordRequest(BaseModel):
    token: str            # 重置token
    new_password: str     # 新密码
```

### 验证码存储结构（内存dict，带TTL）

```python
# captcha_store: {captcha_id: {"code": "abc123", "expires_at": datetime}}
# email_code_store: {email: {"code": "123456", "expires_at": datetime, "sent_at": datetime}}
```

## 文件组织结构

```
backend/app/
├── api/v1/auth.py              # 修改：新增4个路由
├── schemas/auth.py             # 修改：新增4个Schema
├── models/user.py              # 修改：新增phone+email_verified字段
├── core/config.py              # 修改：新增SMTP配置项
├── core/security.py            # 修改：新增验证码生成+邮件发送函数
├── services/
│   ├── captcha_service.py      # 新增：图形验证码生成+校验
│   └── email_service.py        # 新增：邮件发送+验证码管理
frontend/src/
├── pages/auth/
│   ├── LoginPage.tsx           # 修改：验证码+记住账号+忘记密码
│   ├── RegisterPage.tsx       # 修改：手机号+邮箱+验证码
│   └── ResetPasswordPage.tsx  # 新增：重置密码页面
├── services/authApi.ts        # 修改：新增API调用
```

## 风险登记册

| 风险 | 概率 | 影响 | 应对方案 |
|------|------|------|----------|
| 邮件服务不可用 | 中 | 高 | 捕获SMTP异常，友好提示"邮件发送失败" |
| 验证码存储内存泄漏 | 低 | 中 | 每次访问时清理过期条目 |
| 手机号重复注册 | 中 | 中 | 数据库unique约束+注册前检查 |
| 重置链接被拦截 | 低 | 高 | HTTPS + 短有效期30min |

## WBS 任务分解

- **WBS-1**：后端 config.py 新增 SMTP 配置项
- **WBS-2**：后端 User model 新增 phone + email_verified 字段
- **WBS-3**：后端 captcha_service.py（图形验证码生成+校验）
- **WBS-4**：后端 email_service.py（邮件发送+验证码管理）
- **WBS-5**：后端 schemas/auth.py 新增4个Schema
- **WBS-6**：后端 auth.py 新增4个路由（captcha/register/send-code/forgot/reset）
- **WBS-7**：前端 authApi.ts 新增API调用函数
- **WBS-8**：前端 LoginPage.tsx 增加：验证码+记住账号+忘记密码链接
- **WBS-9**：前端 RegisterPage.tsx 重构：手机号+邮箱+验证码
- **WBS-10**：前端 ResetPasswordPage.tsx 新增：重置密码页面
- **WBS-11**：数据库迁移（alembic）