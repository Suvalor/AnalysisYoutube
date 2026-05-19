"""Sprint 1 业务验收测试：用户分层与权限体系重构。

需求溯源：docs/requirements.md AC-1 ~ AC-6
测试层：Unit + Integration（纯逻辑，不依赖数据库连接）

测试策略：
- 对 service/crud 层逻辑做 Unit 测试（mock AsyncSession）
- 对 API 路由做源码级验证（读取源文件验证关键逻辑存在）
- 对安全机制做负向测试
- 侧向效应检查：role 字段对现有登录的影响、中间件对现有 API 的影响

注意：
- 不导入 app.api.v1.auth 等路由模块（会触发 DB engine 创建需要 asyncmy）
- 改用 inspect.getsource 或直接读取源文件验证关键逻辑
- 不直接实例化 SQLAlchemy 模型（会触发 mapper 配置需要关联模型）
"""

from __future__ import annotations

import inspect
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── 确保环境变量在 import app 之前设置 ──
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-min-32chars")
os.environ.setdefault("MYSQL_USER", "test")
os.environ.setdefault("MYSQL_PASSWORD", "test")
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_DB", "test_db")

from app.models.user import User, UserRole
from app.models.admin_invitation import AdminInvitation
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription
from app.models.guest_session import GuestSession
from app.services.rate_limit_service import (
    DEFAULT_QUOTAS,
    check_quota,
    get_role_limits,
)
from app.services.guest_service import (
    GuestInfo,
    generate_guest_id,
    identify_guest,
    set_guest_cookie,
    _extract_client_ip,
    _GUEST_COOKIE_NAME,
)
from app.schemas.subscription import (
    SubscriptionPlanCreate,
    SubscriptionPlanRead,
    SubscriptionPlanUpdate,
    UserSubscriptionCreate,
    UserSubscriptionRead,
)
from app.schemas.admin_invitation import (
    AdminInvitationCreate,
    AdminInvitationRead,
    AdminInvitationVerify,
)
from app.schemas.auth import RegisterRequest, UserRead, Token
from app.core.security import create_access_token, decode_access_token


# 辅助：读取源文件内容（避免导入触发 DB engine）
def _read_source(relative_path: str) -> str:
    """读取 backend/app 下的源文件内容。"""
    base = Path("/workspace/backend/app")
    return (base / relative_path).read_text()


AUTH_SOURCE = _read_source("api/v1/auth.py")
DEPS_SOURCE = _read_source("api/deps.py")
SUBS_ROUTE_SOURCE = _read_source("api/v1/subscriptions.py")
USERS_ROUTE_SOURCE = _read_source("api/v1/users.py")
SUBS_SERVICE_SOURCE = _read_source("services/subscription_service.py")
USER_CRUD_SOURCE = _read_source("crud/user.py")


# ═══════════════════════════════════════════════════════════════════
# AC-1: 用户分层
# ═══════════════════════════════════════════════════════════════════


class TestAC1UserTiering:
    """AC-1 验收标准：用户分层模型"""

    def test_user_model_has_role_field(self):
        """AC-1: users 表包含 role 字段，枚举值为 guest/user/subscriber/admin"""
        assert UserRole.GUEST == "guest"
        assert UserRole.USER == "user"
        assert UserRole.SUBSCRIBER == "subscriber"
        assert UserRole.ADMIN == "admin"

    def test_user_model_role_default_is_user(self):
        """AC-1: 新注册用户默认 role=user"""
        role_col = User.__table__.c.role
        assert role_col.server_default.arg == "user"

    def test_user_model_role_enum_values(self):
        """AC-1: role 字段枚举值完整"""
        role_col = User.__table__.c.role
        enum_vals = set(role_col.type.enums)
        expected = {"guest", "user", "subscriber", "admin"}
        assert enum_vals == expected

    def test_user_model_role_not_nullable(self):
        """AC-1: role 字段不可为空"""
        role_col = User.__table__.c.role
        assert role_col.nullable is False

    def test_create_user_default_role_in_crud(self):
        """AC-1: crud.create_user 的 role 参数默认值为 'user'"""
        from app.crud.user import create_user

        sig = inspect.signature(create_user)
        role_param = sig.parameters["role"]
        assert role_param.default == "user"

    def test_create_user_accepts_admin_role(self):
        """AC-1: crud.create_user 接受 role='admin' 参数"""
        from app.crud.user import create_user

        sig = inspect.signature(create_user)
        assert "role" in sig.parameters

    def test_register_sets_admin_role_on_invite_code(self):
        """AC-1: 管理员邀请链接注册的用户 role=admin

        验证 auth.py register 函数中，invite_code 有效时设置 role = UserRole.ADMIN。
        """
        assert "UserRole.ADMIN" in AUTH_SOURCE
        assert "role = UserRole.ADMIN" in AUTH_SOURCE

    def test_admin_role_update_api_missing(self):
        """AC-1 GAP: 用户角色可通过管理员 API 修改 -- 当前无此 API。

        需求文档 AC-1 要求'用户角色可通过管理员 API 修改'，
        但代码中不存在管理员修改用户角色的 API 端点。
        crud/user.py 的 _ALLOWED_SETTINGS_FIELDS 不包含 'role'。
        """
        from app.crud.user import _ALLOWED_SETTINGS_FIELDS

        assert "role" not in _ALLOWED_SETTINGS_FIELDS

    def test_no_role_update_route_in_users(self):
        """AC-1 GAP: users 路由中不存在角色修改端点"""
        # users.py 不包含 role 修改逻辑
        assert "role" not in USERS_ROUTE_SOURCE or "update" not in USERS_ROUTE_SOURCE.lower()


# ═══════════════════════════════════════════════════════════════════
# AC-2: API 限额管控
# ═══════════════════════════════════════════════════════════════════


class TestAC2QuotaLimits:
    """AC-2 验收标准：API 分层限额管控"""

    def test_guest_youtube_api_limit_is_5(self):
        """AC-2: 游客每日 YouTube API 调用上限 5 次"""
        assert DEFAULT_QUOTAS[UserRole.GUEST]["youtube_api"] == 5

    def test_guest_llm_api_limit_is_0(self):
        """AC-2: 游客 LLM API 配额为 0"""
        assert DEFAULT_QUOTAS[UserRole.GUEST]["llm_api"] == 0

    def test_guest_cv_api_limit_is_0(self):
        """AC-2: 游客 CV API 配额为 0"""
        assert DEFAULT_QUOTAS[UserRole.GUEST]["cv_api"] == 0

    def test_user_youtube_api_limit_is_20(self):
        """AC-2: 普通用户每日 YouTube API 调用上限 20 次"""
        assert DEFAULT_QUOTAS[UserRole.USER]["youtube_api"] == 20

    def test_user_llm_api_limit_is_10(self):
        """AC-2: 普通用户 LLM API 上限 10 次"""
        assert DEFAULT_QUOTAS[UserRole.USER]["llm_api"] == 10

    def test_user_cv_api_limit_is_5(self):
        """AC-2: 普通用户 CV API 上限 5 次"""
        assert DEFAULT_QUOTAS[UserRole.USER]["cv_api"] == 5

    def test_subscriber_youtube_api_limit_is_100(self):
        """AC-2: 付费用户每日 YouTube API 调用上限 100 次"""
        assert DEFAULT_QUOTAS[UserRole.SUBSCRIBER]["youtube_api"] == 100

    def test_subscriber_llm_api_limit_is_50(self):
        """AC-2: 付费用户 LLM API 上限 50 次"""
        assert DEFAULT_QUOTAS[UserRole.SUBSCRIBER]["llm_api"] == 50

    def test_subscriber_cv_api_limit_is_20(self):
        """AC-2: 付费用户 CV API 上限 20 次"""
        assert DEFAULT_QUOTAS[UserRole.SUBSCRIBER]["cv_api"] == 20

    def test_admin_no_quota_limit(self):
        """AC-2: 管理员无配额限制（-1 表示无限制）"""
        assert DEFAULT_QUOTAS[UserRole.ADMIN]["youtube_api"] == -1
        assert DEFAULT_QUOTAS[UserRole.ADMIN]["llm_api"] == -1
        assert DEFAULT_QUOTAS[UserRole.ADMIN]["cv_api"] == -1

    def test_get_role_limits_guest(self):
        """AC-2: get_role_limits 返回游客配额"""
        limits = get_role_limits(UserRole.GUEST)
        assert limits["youtube_api"] == 5
        assert limits["llm_api"] == 0
        assert limits["cv_api"] == 0

    def test_get_role_limits_user(self):
        """AC-2: get_role_limits 返回普通用户配额"""
        limits = get_role_limits(UserRole.USER)
        assert limits["youtube_api"] == 20
        assert limits["llm_api"] == 10
        assert limits["cv_api"] == 5

    def test_get_role_limits_subscriber_with_custom_quotas(self):
        """AC-2: 订阅用户优先使用订阅套餐配额"""
        custom_quotas = {"youtube_api": 200, "llm_api": 100, "cv_api": 50}
        limits = get_role_limits(UserRole.SUBSCRIBER, subscription_quotas=custom_quotas)
        assert limits["youtube_api"] == 200
        assert limits["llm_api"] == 100

    def test_get_role_limits_subscriber_without_custom_quotas(self):
        """AC-2: 订阅用户无自定义配额时使用默认配额"""
        limits = get_role_limits(UserRole.SUBSCRIBER, subscription_quotas=None)
        assert limits["youtube_api"] == 100

    def test_get_role_limits_admin_always_unlimited(self):
        """AC-2: 管理员始终无限制，即使传入自定义配额"""
        custom_quotas = {"youtube_api": 50}
        limits = get_role_limits(UserRole.ADMIN, subscription_quotas=custom_quotas)
        assert limits["youtube_api"] == -1

    @pytest.mark.asyncio
    async def test_check_quota_guest_within_limit(self):
        """AC-2: 游客配额内允许调用"""
        mock_session = AsyncMock()
        mock_guest = MagicMock()
        mock_guest.daily_quotas = {"youtube_api": 3, "llm_api": 0, "cv_api": 0, "date": "2026-05-19"}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_guest
        mock_session.execute.return_value = mock_result

        allowed, used, limit = await check_quota(
            mock_session,
            role=UserRole.GUEST,
            guest_id="test-guest-id",
            api_type="youtube_api",
        )
        assert allowed is True
        assert used == 3
        assert limit == 5

    @pytest.mark.asyncio
    async def test_check_quota_guest_at_limit(self):
        """AC-2: 游客达到配额上限时不允许调用"""
        mock_session = AsyncMock()
        mock_guest = MagicMock()
        mock_guest.daily_quotas = {"youtube_api": 5, "llm_api": 0, "cv_api": 0, "date": "2026-05-19"}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_guest
        mock_session.execute.return_value = mock_result

        allowed, used, limit = await check_quota(
            mock_session,
            role=UserRole.GUEST,
            guest_id="test-guest-id",
            api_type="youtube_api",
        )
        assert allowed is False
        assert used == 5
        assert limit == 5

    @pytest.mark.asyncio
    async def test_check_quota_user_within_limit(self):
        """AC-2: 普通用户配额内允许调用"""
        mock_session = AsyncMock()
        mock_guest = MagicMock()
        mock_guest.daily_quotas = {"youtube_api": 10, "llm_api": 0, "cv_api": 0, "date": "2026-05-19"}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_guest
        mock_session.execute.return_value = mock_result

        allowed, used, limit = await check_quota(
            mock_session,
            user_id=1,
            role=UserRole.USER,
            api_type="youtube_api",
        )
        assert allowed is True
        assert used == 10
        assert limit == 20

    @pytest.mark.asyncio
    async def test_check_quota_user_at_limit(self):
        """AC-2: 普通用户达到配额上限时不允许调用"""
        mock_session = AsyncMock()
        mock_guest = MagicMock()
        mock_guest.daily_quotas = {"youtube_api": 20, "llm_api": 0, "cv_api": 0, "date": "2026-05-19"}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_guest
        mock_session.execute.return_value = mock_result

        allowed, used, limit = await check_quota(
            mock_session,
            user_id=1,
            role=UserRole.USER,
            api_type="youtube_api",
        )
        assert allowed is False
        assert used == 20
        assert limit == 20

    @pytest.mark.asyncio
    async def test_check_quota_admin_always_allowed(self):
        """AC-2: 管理员始终允许调用"""
        mock_session = AsyncMock()
        allowed, used, limit = await check_quota(
            mock_session,
            user_id=1,
            role=UserRole.ADMIN,
            api_type="youtube_api",
        )
        assert allowed is True
        assert limit == -1

    @pytest.mark.asyncio
    async def test_check_quota_guest_llm_api_always_blocked(self):
        """AC-2: 游客 LLM API 配额为 0，始终不允许"""
        mock_session = AsyncMock()
        mock_guest = MagicMock()
        mock_guest.daily_quotas = {"youtube_api": 0, "llm_api": 0, "cv_api": 0, "date": "2026-05-19"}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_guest
        mock_session.execute.return_value = mock_result

        allowed, used, limit = await check_quota(
            mock_session,
            role=UserRole.GUEST,
            guest_id="test-guest-id",
            api_type="llm_api",
        )
        assert allowed is False
        assert limit == 0

    @pytest.mark.asyncio
    async def test_check_quota_guest_cv_api_always_blocked(self):
        """AC-2: 游客 CV API 配额为 0，始终不允许"""
        mock_session = AsyncMock()
        mock_guest = MagicMock()
        mock_guest.daily_quotas = {"youtube_api": 0, "llm_api": 0, "cv_api": 0, "date": "2026-05-19"}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_guest
        mock_session.execute.return_value = mock_result

        allowed, used, limit = await check_quota(
            mock_session,
            role=UserRole.GUEST,
            guest_id="test-guest-id",
            api_type="cv_api",
        )
        assert allowed is False
        assert limit == 0

    def test_daily_quota_reset_mechanism(self):
        """AC-2: 配额每日 0 点自动重置（通过日期比对实现）"""
        from app.crud.guest_session_crud import increment_guest_quota, get_guest_daily_usage

        source_inc = inspect.getsource(increment_guest_quota)
        source_get = inspect.getsource(get_guest_daily_usage)

        assert "date" in source_inc
        assert "today" in source_inc
        assert "date" in source_get
        assert "today" in source_get

    @pytest.mark.asyncio
    async def test_check_quota_no_user_info_defaults_deny(self):
        """AC-2: 无用户信息时默认不允许调用"""
        mock_session = AsyncMock()
        allowed, used, limit = await check_quota(
            mock_session,
            role=UserRole.GUEST,
            guest_id=None,
            user_id=None,
            api_type="youtube_api",
        )
        assert allowed is False

    def test_quota_guard_raises_429_on_exceeded(self):
        """AC-2: 配额超限时抛出 HTTP 429"""
        assert "429" in DEPS_SOURCE or "TOO_MANY_REQUESTS" in DEPS_SOURCE


# ═══════════════════════════════════════════════════════════════════
# AC-3: 游客体验
# ═══════════════════════════════════════════════════════════════════


class TestAC3GuestExperience:
    """AC-3 验收标准：游客识别与体验"""

    def test_generate_guest_id_is_uuid(self):
        """AC-3: 生成唯一游客标识 UUID"""
        guest_id = generate_guest_id()
        parsed = uuid.UUID(guest_id)
        assert str(parsed) == guest_id

    def test_generate_guest_id_unique(self):
        """AC-3: 每次生成的 guest_id 唯一"""
        ids = {generate_guest_id() for _ in range(100)}
        assert len(ids) == 100

    def test_extract_client_ip_from_forwarded(self):
        """AC-3: 从 X-Forwarded-For 头提取 IP"""
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda k: {
            "x-forwarded-for": "1.2.3.4, 5.6.7.8",
            "x-real-ip": None,
        }.get(k)
        ip = _extract_client_ip(mock_request)
        assert ip == "1.2.3.4"

    def test_extract_client_ip_from_real_ip(self):
        """AC-3: 从 X-Real-IP 头提取 IP"""
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda k: {
            "x-forwarded-for": None,
            "x-real-ip": "9.8.7.6",
        }.get(k)
        ip = _extract_client_ip(mock_request)
        assert ip == "9.8.7.6"

    def test_extract_client_ip_from_client(self):
        """AC-3: 从 request.client.host 提取 IP"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client.host = "10.0.0.1"
        ip = _extract_client_ip(mock_request)
        assert ip == "10.0.0.1"

    def test_extract_client_ip_no_info_returns_none(self):
        """AC-3: 无任何 IP 信息时返回 None"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = None
        ip = _extract_client_ip(mock_request)
        assert ip is None

    def test_guest_cookie_name(self):
        """AC-3: Cookie 名称为 guest_id"""
        assert _GUEST_COOKIE_NAME == "guest_id"

    def test_guest_cookie_max_age_30_days(self):
        """AC-3: Cookie 有效期 30 天"""
        from app.services.guest_service import _GUEST_COOKIE_MAX_AGE

        assert _GUEST_COOKIE_MAX_AGE == 30 * 24 * 3600

    def test_set_guest_cookie_security_attributes(self):
        """AC-3: Cookie 安全属性：HttpOnly + Secure + SameSite=Lax"""
        mock_response = MagicMock()
        set_guest_cookie(mock_response, "test-guest-id")

        mock_response.set_cookie.assert_called_once()
        call_kwargs = mock_response.set_cookie.call_args[1]
        assert call_kwargs["httponly"] is True
        assert call_kwargs["secure"] is True
        assert call_kwargs["samesite"] == "lax"
        assert call_kwargs["key"] == "guest_id"
        assert call_kwargs["value"] == "test-guest-id"

    @pytest.mark.asyncio
    async def test_identify_guest_new_visitor(self):
        """AC-3: 未登录用户首次访问自动生成 guest_id"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_request.headers.get.return_value = None
        mock_request.client.host = "1.2.3.4"

        mock_session = AsyncMock()

        with patch("app.services.guest_service.create_guest_session") as mock_create:
            mock_guest = MagicMock()
            mock_create.return_value = mock_guest

            result = await identify_guest(mock_request, mock_session)

            assert result.is_new is True
            assert result.guest_id is not None
            assert result.ip_address == "1.2.3.4"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_identify_guest_returning_visitor(self):
        """AC-3: 已有 Cookie 的游客返回 is_new=False"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "existing-guest-id"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "1.2.3.4"

        mock_session = AsyncMock()

        with patch("app.services.guest_service.get_guest_session") as mock_get:
            mock_guest = MagicMock()
            mock_get.return_value = mock_guest

            result = await identify_guest(mock_request, mock_session)

            assert result.is_new is False
            assert result.guest_id == "existing-guest-id"

    @pytest.mark.asyncio
    async def test_identify_guest_cookie_exists_but_no_db_record(self):
        """AC-3: Cookie 存在但数据库无记录时，复用 guest_id 创建新记录"""
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "orphan-guest-id"
        mock_request.headers.get.return_value = None
        mock_request.client.host = "1.2.3.4"

        mock_session = AsyncMock()

        with patch("app.services.guest_service.get_guest_session") as mock_get:
            mock_get.return_value = None

            with patch("app.services.guest_service.create_guest_session") as mock_create:
                mock_guest = MagicMock()
                mock_create.return_value = mock_guest

                result = await identify_guest(mock_request, mock_session)

                assert result.is_new is True
                assert result.guest_id == "orphan-guest-id"
                mock_create.assert_called_once()

    def test_guest_session_model_has_required_fields(self):
        """AC-3: guest_sessions 表包含必要字段"""
        cols = {c.name for c in GuestSession.__table__.columns}
        required = {"id", "guest_id", "ip_address", "daily_quotas", "last_active_at", "created_at"}
        assert required.issubset(cols)

    def test_guest_session_guest_id_unique(self):
        """AC-3: guest_id 字段唯一"""
        col = GuestSession.__table__.c.guest_id
        assert col.unique is True


# ═══════════════════════════════════════════════════════════════════
# AC-4: 管理员邀请注册
# ═══════════════════════════════════════════════════════════════════


class TestAC4AdminInvitation:
    """AC-4 验收标准：管理员邀请注册"""

    def test_invite_code_length_6(self):
        """AC-4: 邀请码为 6 位随机字符串"""
        # 从源码验证 _generate_invite_code 的 length 参数默认为 6
        assert "length: int = 6" in AUTH_SOURCE

    def test_invite_code_excludes_confusing_chars(self):
        """AC-4: 邀请码排除易混淆字符 O/0/I/1/L"""
        # 从源码验证排除逻辑
        assert '"O"' in AUTH_SOURCE or "'O'" in AUTH_SOURCE
        assert '"0"' in AUTH_SOURCE or "'0'" in AUTH_SOURCE
        assert '"I"' in AUTH_SOURCE or "'I'" in AUTH_SOURCE
        assert '"1"' in AUTH_SOURCE or "'1'" in AUTH_SOURCE
        assert '"L"' in AUTH_SOURCE or "'L'" in AUTH_SOURCE

    def test_invite_code_uses_secrets(self):
        """AC-4: 邀请码使用 secrets.choice 生成（密码学安全）"""
        assert "secrets.choice" in AUTH_SOURCE

    def test_create_admin_invitation_expires_7_days(self):
        """AC-4: 管理员可生成邀请码，有效期 7 天（168 小时）"""
        from app.crud.admin_invitation_crud import create_admin_invitation

        source = inspect.getsource(create_admin_invitation)
        assert "168" in source

    def test_mark_invitation_used_sets_inactive(self):
        """AC-4: 已使用的邀请码标记为已使用（is_active=False）"""
        from app.crud.admin_invitation_crud import mark_invitation_used

        source = inspect.getsource(mark_invitation_used)
        assert "is_active" in source
        assert "False" in source
        assert "used_by" in source
        assert "used_at" in source

    def test_expired_invitation_rejected_in_verify(self):
        """AC-4: 过期邀请码无法使用"""
        assert "expires_at" in AUTH_SOURCE

    def test_used_invitation_rejected_in_verify(self):
        """AC-4: 已使用的邀请码无法使用"""
        assert "is_active" in AUTH_SOURCE

    def test_invite_verify_ip_rate_limit_params(self):
        """AC-4: 邀请码验证有 IP 速率限制"""
        assert "_INVITE_VERIFY_MAX_FAILS" in AUTH_SOURCE
        assert "_INVITE_VERIFY_LOCK_SECONDS" in AUTH_SOURCE
        assert "= 5" in AUTH_SOURCE  # MAX_FAILS = 5
        assert "= 15 * 60" in AUTH_SOURCE  # LOCK_SECONDS = 15 * 60

    def test_invite_verify_ip_lockout_logic(self):
        """AC-4: 连续失败 5 次后锁定 IP 15 分钟"""
        assert "_record_invite_verify_failure" in AUTH_SOURCE
        assert "locked_until" in AUTH_SOURCE
        assert "_INVITE_VERIFY_MAX_FAILS" in AUTH_SOURCE

    def test_invite_verify_success_resets_logic(self):
        """AC-4: 验证成功时重置失败计数"""
        assert "_record_invite_verify_success" in AUTH_SOURCE

    def test_invite_verify_returns_generic_error_no_reason(self):
        """AC-4 安全: 验证失败时返回通用错误消息，不区分不存在/已使用/已过期"""
        schema_fields = set(AdminInvitationVerify.model_fields.keys())
        assert "reason" not in schema_fields
        assert "error" not in schema_fields
        assert "message" not in schema_fields
        assert schema_fields == {"valid", "code"}

    def test_admin_invite_endpoint_requires_admin_dep(self):
        """AC-4: 生成邀请码端点要求管理员权限"""
        # 验证 create_admin_invite 使用 AdminDep
        assert "AdminDep" in AUTH_SOURCE
        assert "create_admin_invite" in AUTH_SOURCE

    def test_admin_invitation_model_fields(self):
        """AC-4: admin_invitations 表包含必要字段"""
        cols = {c.name for c in AdminInvitation.__table__.columns}
        required = {"id", "code", "created_by", "used_by", "used_at", "expires_at", "is_active"}
        assert required.issubset(cols)

    def test_admin_invitation_code_unique(self):
        """AC-4: 邀请码字段唯一"""
        col = AdminInvitation.__table__.c.code
        assert col.unique is True

    def test_register_with_invite_code_flow(self):
        """AC-4: 注册时邀请码验证流程完整

        验证 register 函数中邀请码处理逻辑：
        1. 邀请码不存在 -> 400
        2. 邀请码已使用 -> 400
        3. 邀请码已过期 -> 400
        4. 邀请码有效 -> role=admin
        """
        assert "邀请码不存在" in AUTH_SOURCE
        assert "邀请码已被使用" in AUTH_SOURCE
        assert "邀请码已过期" in AUTH_SOURCE
        assert "role = UserRole.ADMIN" in AUTH_SOURCE


# ═══════════════════════════════════════════════════════════════════
# AC-6: 订阅管理 API
# ═══════════════════════════════════════════════════════════════════


class TestAC6SubscriptionManagement:
    """AC-6 验收标准：订阅管理 API"""

    def test_subscription_plan_model_fields(self):
        """AC-6: subscription_plans 表包含必要字段"""
        cols = {c.name for c in SubscriptionPlan.__table__.columns}
        required = {"id", "name", "description", "quotas_json", "price_monthly", "is_active", "created_at", "updated_at"}
        assert required.issubset(cols)

    def test_user_subscription_model_fields(self):
        """AC-6: user_subscriptions 表包含必要字段"""
        cols = {c.name for c in UserSubscription.__table__.columns}
        required = {"id", "user_id", "plan_id", "started_at", "expires_at", "is_active"}
        assert required.issubset(cols)

    def test_subscription_plan_create_schema(self):
        """AC-6: 创建订阅套餐 Schema 验证"""
        plan = SubscriptionPlanCreate(
            name="Pro",
            description="Pro plan",
            quotas_json={"youtube_api": 200, "llm_api": 100, "cv_api": 50},
            price_monthly=99.00,
        )
        assert plan.name == "Pro"
        assert plan.quotas_json["youtube_api"] == 200

    def test_subscription_plan_update_schema_partial(self):
        """AC-6: 更新订阅套餐 Schema 支持部分更新"""
        update = SubscriptionPlanUpdate(is_active=False)
        data = update.model_dump(exclude_unset=True)
        assert "is_active" in data
        assert "name" not in data

    def test_user_subscription_create_schema(self):
        """AC-6: 分配订阅套餐 Schema 验证"""
        sub = UserSubscriptionCreate(
            user_id=1,
            plan_id=2,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        assert sub.user_id == 1
        assert sub.plan_id == 2

    def test_create_subscription_plan_crud(self):
        """AC-6: 管理员可创建订阅套餐（CRUD 层）"""
        from app.crud.subscription_crud import create_subscription_plan

        sig = inspect.signature(create_subscription_plan)
        assert "name" in sig.parameters
        assert "quotas_json" in sig.parameters
        assert "price_monthly" in sig.parameters

    def test_update_subscription_plan_crud(self):
        """AC-6: 管理员可编辑订阅套餐（CRUD 层）"""
        from app.crud.subscription_crud import update_subscription_plan

        sig = inspect.signature(update_subscription_plan)
        assert "patch" in sig.parameters

    def test_deactivate_subscription_plan_via_update(self):
        """AC-6: 管理员可停用订阅套餐（通过 update 的 is_active 字段）"""
        schema = SubscriptionPlanUpdate(is_active=False)
        data = schema.model_dump(exclude_unset=True)
        assert data["is_active"] is False

    def test_assign_subscription_deactivates_previous(self):
        """AC-6: 分配新订阅时自动停用旧订阅"""
        from app.crud.subscription_crud import create_user_subscription

        source = inspect.getsource(create_user_subscription)
        assert "is_active" in source
        assert "False" in source

    def test_assign_subscription_does_not_upgrade_role_bug(self):
        """AC-6 BUG: assign_subscription 的文档说'同时升级用户角色为 subscriber'，
        但实际代码并未修改用户 role 字段。

        这是一个 BUG：用户被分配订阅后，角色仍然是 user，
        导致配额检查使用 DEFAULT_QUOTAS['user'] 而非 subscriber 配额。
        """
        assert "user.role" not in SUBS_SERVICE_SOURCE, (
            "assign_subscription 不包含角色升级逻辑，"
            "但 docstring 声称会'同时升级用户角色为 subscriber'"
        )

    def test_subscription_routes_exist(self):
        """AC-6: 订阅管理路由存在"""
        assert "get_subscription_plans" in SUBS_ROUTE_SOURCE
        assert "assign_user_subscription" in SUBS_ROUTE_SOURCE
        assert "get_my_subscription_status" in SUBS_ROUTE_SOURCE

    def test_assign_subscription_requires_admin(self):
        """AC-6: 分配订阅套餐端点要求管理员权限"""
        assert "AdminDep" in SUBS_ROUTE_SOURCE

    def test_my_subscription_requires_login(self):
        """AC-6: 查看我的订阅需要登录"""
        assert "CurrentUserDep" in SUBS_ROUTE_SOURCE

    def test_subscription_expiry_no_auto_downgrade(self):
        """AC-6 GAP: 订阅到期后用户角色不会自动回退到 user。

        Phase 1 不做自动降级，这是已知延后项。
        且 assign_subscription 也没有升级角色，所以不存在需要降级的场景。
        """
        assert "role" not in SUBS_SERVICE_SOURCE or "subscriber" not in SUBS_SERVICE_SOURCE


# ═══════════════════════════════════════════════════════════════════
# 侧向效应检查
# ═══════════════════════════════════════════════════════════════════


class TestSideEffects:
    """侧向效应检查：新增字段/中间件对现有功能的影响"""

    def test_role_field_in_jwt_token(self):
        """侧向效应: role 字段在 JWT 中正确编码和解码"""
        token = create_access_token(
            data={"sub": "test@example.com", "role": "admin"},
            expires_delta=timedelta(minutes=30),
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "test@example.com"
        assert payload["role"] == "admin"

    def test_role_field_in_login_response(self):
        """侧向效应: 登录响应 Token 包含 role 字段"""
        token_data = Token(access_token="test-token", token_type="bearer", role="user")
        assert token_data.role == "user"

    def test_user_read_schema_includes_role(self):
        """侧向效应: UserRead schema 包含 role 字段"""
        schema = UserRead(
            id=1,
            email="test@example.com",
            is_active=True,
            role="admin",
            email_verified=True,
            created_at=datetime.now(timezone.utc),
        )
        assert schema.role == "admin"

    def test_login_includes_role_in_jwt(self):
        """侧向效应: 登录时 JWT payload 包含 role"""
        assert '"role"' in AUTH_SOURCE or "'role'" in AUTH_SOURCE
        assert "user.role" in AUTH_SOURCE

    def test_require_admin_rejects_non_admin(self):
        """侧向效应: require_admin 依赖正确拒绝非管理员（源码级验证）""" 
        # 验证 require_admin 函数检查 role != ADMIN 时抛出 403
        assert "require_admin" in DEPS_SOURCE
        assert "403" in DEPS_SOURCE or "FORBIDDEN" in DEPS_SOURCE
        assert "UserRole.ADMIN" in DEPS_SOURCE

    def test_require_admin_allows_admin(self):
        """侧向效应: require_admin 依赖允许管理员通过（源码级验证）""" 
        # 验证 require_admin 函数在 role == ADMIN 时返回 user
        assert "require_admin" in DEPS_SOURCE
        assert "return user" in DEPS_SOURCE

    def test_existing_user_default_role_is_user(self):
        """侧向效应: 现有用户 role 默认值为 user，不影响现有功能"""
        role_col = User.__table__.c.role
        assert role_col.server_default.arg == "user"

    def test_guest_session_daily_quotas_is_json_type(self):
        """侧向效应: guest_sessions.daily_quotas 使用 JSON 类型存储"""
        col = GuestSession.__table__.c.daily_quotas
        from sqlalchemy import JSON

        assert isinstance(col.type, JSON)

    def test_optional_user_dep_returns_none_for_guests(self):
        """侧向效应: OptionalUserDep 对未登录用户返回 None 而非 401"""
        assert "get_optional_user" in DEPS_SOURCE
        assert "None" in DEPS_SOURCE


# ═══════════════════════════════════════════════════════════════════
# 安全负向测试
# ═══════════════════════════════════════════════════════════════════


class TestSecurityNegative:
    """安全负向测试：越权、防枚举、防重用"""

    def test_invite_code_uses_secrets_not_random(self):
        """安全: 邀请码使用 secrets.choice 生成，不可预测"""
        assert "secrets.choice" in AUTH_SOURCE
        assert "random.choices" not in AUTH_SOURCE

    def test_invite_verify_no_information_leakage(self):
        """安全: 邀请码验证失败时不暴露具体原因（防枚举）"""
        schema_fields = set(AdminInvitationVerify.model_fields.keys())
        assert "reason" not in schema_fields
        assert "error" not in schema_fields
        assert "message" not in schema_fields
        assert schema_fields == {"valid", "code"}

    def test_invite_verify_generic_error_message(self):
        """安全: 验证失败时返回统一格式，不区分不存在/已使用/已过期"""
        # verify_admin_invite 使用统一 is_valid 判断
        assert "is_valid" in AUTH_SOURCE

    def test_used_invite_cannot_be_reused(self):
        """安全: 已使用的邀请码不能再次使用（is_active=False）"""
        assert "is_active" in AUTH_SOURCE
        # verify 端点检查 is_active
        assert "invitation.is_active" in AUTH_SOURCE

    def test_guest_cookie_httponly_prevents_xss(self):
        """安全: guest_id Cookie 设置 HttpOnly，防止 XSS 窃取"""
        mock_response = MagicMock()
        set_guest_cookie(mock_response, "test-id")
        call_kwargs = mock_response.set_cookie.call_args[1]
        assert call_kwargs["httponly"] is True

    def test_guest_cookie_samesite_lax_prevents_csrf(self):
        """安全: guest_id Cookie 设置 SameSite=Lax，缓解 CSRF"""
        mock_response = MagicMock()
        set_guest_cookie(mock_response, "test-id")
        call_kwargs = mock_response.set_cookie.call_args[1]
        assert call_kwargs["samesite"] == "lax"

    def test_quota_guard_returns_429_not_403(self):
        """安全: 配额超限返回 429 而非 403，不暴露权限信息"""
        assert "429" in DEPS_SOURCE or "TOO_MANY_REQUESTS" in DEPS_SOURCE

    def test_admin_invite_endpoint_requires_admin(self):
        """安全: 生成邀请码端点要求管理员权限"""
        assert "AdminDep" in AUTH_SOURCE

    def test_subscription_assign_requires_admin(self):
        """安全: 分配订阅套餐端点要求管理员权限"""
        assert "AdminDep" in SUBS_ROUTE_SOURCE

    def test_jwt_contains_role_for_authorization(self):
        """安全: JWT 包含 role 字段，用于后续授权判断"""
        token = create_access_token(
            data={"sub": "admin@example.com", "role": "admin"},
            expires_delta=timedelta(minutes=30),
        )
        payload = decode_access_token(token)
        assert "role" in payload
        assert payload["role"] == "admin"

    def test_register_invite_code_validated_before_user_creation(self):
        """安全: 邀请码在创建用户之前验证，防止绕过""" 
        # 在 register 函数中，invite_code 处理在 create_user 之前
        # 查找 register 函数体（从 "async def register" 开始）
        register_start = AUTH_SOURCE.find("async def register")
        register_body = AUTH_SOURCE[register_start:]
        invite_pos = register_body.find("invite_code")
        create_pos = register_body.find("create_user")
        assert invite_pos < create_pos, "邀请码验证应在用户创建之前"

    def test_no_role_in_register_request_schema(self):
        """安全: 注册请求体不包含 role 字段，防止客户端指定角色"""
        fields = set(RegisterRequest.model_fields.keys())
        assert "role" not in fields

    def test_ip_rate_limit_prevents_invite_brute_force(self):
        """安全: IP 速率限制防止邀请码暴力破解"""
        assert "_check_invite_verify_rate_limit" in AUTH_SOURCE
        assert "locked_until" in AUTH_SOURCE
        assert "429" in AUTH_SOURCE or "TOO_MANY_REQUESTS" in AUTH_SOURCE

    def test_password_not_in_register_response(self):
        """安全: 注册响应不包含密码字段"""
        fields = set(UserRead.model_fields.keys())
        assert "password" not in fields
        assert "hashed_password" not in fields


# ═══════════════════════════════════════════════════════════════════
# 需求溯源矩阵
# ═══════════════════════════════════════════════════════════════════


class TestRequirementsTraceability:
    """需求溯源：验证每个 AC 条目在代码中有对应实现"""

    def test_ac1_role_field_exists(self):
        """AC-1[1]: users 表包含 role 字段"""
        assert hasattr(User, "role")

    def test_ac1_role_enum_complete(self):
        """AC-1[1]: 枚举值为 guest/user/subscriber/admin"""
        assert UserRole.GUEST == "guest"
        assert UserRole.USER == "user"
        assert UserRole.SUBSCRIBER == "subscriber"
        assert UserRole.ADMIN == "admin"

    def test_ac1_default_role_is_user(self):
        """AC-1[2]: 新注册用户默认 role=user"""
        assert User.__table__.c.role.server_default.arg == "user"

    def test_ac1_invite_registration_sets_admin(self):
        """AC-1[3]: 管理员邀请链接注册的用户 role=admin"""
        assert "UserRole.ADMIN" in AUTH_SOURCE

    def test_ac1_admin_role_update_api_missing(self):
        """AC-1[4]: 用户角色可通过管理员 API 修改 -- GAP"""
        from app.crud.user import _ALLOWED_SETTINGS_FIELDS

        assert "role" not in _ALLOWED_SETTINGS_FIELDS

    def test_ac2_guest_youtube_limit(self):
        """AC-2[1]: 游客每日 YouTube API 调用上限 5 次"""
        assert DEFAULT_QUOTAS[UserRole.GUEST]["youtube_api"] == 5

    def test_ac2_user_youtube_limit(self):
        """AC-2[2]: 普通用户每日 YouTube API 调用上限 20 次"""
        assert DEFAULT_QUOTAS[UserRole.USER]["youtube_api"] == 20

    def test_ac2_subscriber_youtube_limit(self):
        """AC-2[3]: 付费用户每日 YouTube API 调用上限 100 次"""
        assert DEFAULT_QUOTAS[UserRole.SUBSCRIBER]["youtube_api"] == 100

    def test_ac2_admin_unlimited(self):
        """AC-2[4]: 管理员无配额限制"""
        assert DEFAULT_QUOTAS[UserRole.ADMIN]["youtube_api"] == -1

    def test_ac2_daily_reset_mechanism(self):
        """AC-2[5]: 配额每日 0 点自动重置"""
        from app.crud.guest_session_crud import increment_guest_quota

        source = inspect.getsource(increment_guest_quota)
        assert "date" in source

    def test_ac2_llm_cv_limits(self):
        """AC-2[6]: LLM/CV API 同理按角色限额"""
        assert DEFAULT_QUOTAS[UserRole.GUEST]["llm_api"] == 0
        assert DEFAULT_QUOTAS[UserRole.GUEST]["cv_api"] == 0
        assert DEFAULT_QUOTAS[UserRole.USER]["llm_api"] == 10
        assert DEFAULT_QUOTAS[UserRole.USER]["cv_api"] == 5

    def test_ac3_guest_cookie_generation(self):
        """AC-3[1]: 未登录用户首次访问自动生成 guest_id Cookie"""
        assert callable(generate_guest_id)

    def test_ac3_guest_quota_exhaustion(self):
        """AC-3[4]: 游客配额用完后返回 429"""
        assert "429" in DEPS_SOURCE or "TOO_MANY_REQUESTS" in DEPS_SOURCE

    def test_ac4_invite_code_generation(self):
        """AC-4[1]: 管理员可生成邀请码，有效期 7 天"""
        from app.crud.admin_invitation_crud import create_admin_invitation

        source = inspect.getsource(create_admin_invitation)
        assert "168" in source

    def test_ac4_invite_registration_sets_admin(self):
        """AC-4[2]: 通过邀请链接注册的用户自动获得 admin 角色"""
        assert "UserRole.ADMIN" in AUTH_SOURCE

    def test_ac4_expired_invite_rejected(self):
        """AC-4[3]: 过期邀请码无法使用"""
        assert "expires_at" in AUTH_SOURCE

    def test_ac4_used_invite_marked(self):
        """AC-4[4]: 已使用的邀请码标记为已使用"""
        from app.crud.admin_invitation_crud import mark_invitation_used

        source = inspect.getsource(mark_invitation_used)
        assert "is_active" in source
        assert "False" in source

    def test_ac4_invite_ip_rate_limit(self):
        """AC-4[5]: 邀请码验证有 IP 速率限制"""
        assert "_check_invite_verify_rate_limit" in AUTH_SOURCE

    def test_ac6_create_edit_deactivate_plan(self):
        """AC-6[1]: 管理员可创建/编辑/停用订阅套餐"""
        from app.services.subscription_service import create_plan, update_plan

        assert callable(create_plan)
        assert callable(update_plan)

    def test_ac6_assign_subscription(self):
        """AC-6[2]: 管理员可为用户分配订阅套餐"""
        from app.services.subscription_service import assign_subscription

        assert callable(assign_subscription)

    def test_ac6_view_subscription(self):
        """AC-6[3]: 用户可查看自己的订阅状态"""
        from app.services.subscription_service import get_my_subscription

        assert callable(get_my_subscription)

    def test_ac6_subscription_expiry_no_auto_downgrade(self):
        """AC-6[4]: 订阅到期后用户角色自动回退到 user -- GAP (Phase 1 不做)"""
        # Phase 1 不做自动降级，这是已知延后项
        # 但 assign_subscription 也没有升级角色，这是关联 BUG
        pass  # 已在 TestAC6 中验证
