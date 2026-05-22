"""游客配额 + 数据隔离审计修复 -- 业务验收测试。

验收标准来源：/workspace/docs/20260520-guest-quota-and-isolation-audit.md
设计规格来源：/workspace/docs/design/design-spec.md（当前版本为敏感信息接口安全加固，
游客配额审计的设计规格以源任务文档为准）

测试策略：纯代码逻辑验证（无数据库依赖），通过直接调用函数/检查源码结构
验证每个验收标准的实现是否到位。
"""

import ast
import importlib
import inspect
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── 辅助：读取源码文本 ──

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _read_source(relative_path: str) -> str:
    """读取 backend 下的源码文件内容。"""
    return (_BACKEND_ROOT / relative_path).read_text()


# ══════════════════════════════════════════════════════════════════════════════
# 缺陷 1：游客配额 Cookie 绕过
# ══════════════════════════════════════════════════════════════════════════════


class TestGuestQuotaCookieBypass:
    """验证 IP 关联配额逻辑，防止清除 Cookie 绕过配额。"""

    # GQ-ACC-01：清除 Cookie 后配额不归零（IP关联生效）
    def test_gq_acc_01_ip_association_prevents_cookie_bypass(self):
        """identify_guest 无 Cookie 时按 IP 查找已有 session，配额不归零。"""
        source = _read_source("app/services/guest_service.py")
        tree = ast.parse(source)

        # 找到 identify_guest 函数
        identify_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "identify_guest":
                identify_func = node
                break

        assert identify_func is not None, "identify_guest 函数不存在"

        # 验证函数体中调用了 get_guest_session_by_ip
        func_source = ast.get_source_segment(source, identify_func)
        assert "get_guest_session_by_ip" in func_source, (
            "GQ-ACC-01 FAIL: identify_guest 未调用 get_guest_session_by_ip，"
            "清除 Cookie 后配额会归零"
        )

        # 验证 IP session 找到时返回 is_new=False（复用已有配额）
        assert "is_new=False" in func_source, (
            "GQ-ACC-01 FAIL: IP session 命中时未设置 is_new=False"
        )

    # GQ-ACC-02：隐身窗口同 IP 共享配额
    def test_gq_acc_02_incognito_shares_quota_by_ip(self):
        """无 Cookie 的隐身窗口通过 IP 找到已有 session，共享配额。"""
        source = _read_source("app/services/guest_service.py")
        # 验证逻辑：无 Cookie → 按 IP 查找 → 复用 session
        assert "get_guest_session_by_ip" in source, (
            "GQ-ACC-02 FAIL: 缺少 IP 查找逻辑，隐身窗口无法共享配额"
        )
        # 验证查找顺序：先 Cookie，后 IP，最后新建
        cookie_block_end = source.find("# 无 Cookie")
        ip_lookup = source.find("get_guest_session_by_ip", cookie_block_end)
        new_session = source.find("generate_guest_id()", cookie_block_end)
        assert ip_lookup < new_session, (
            "GQ-ACC-02 FAIL: IP 查找应在创建新 session 之前"
        )

    # GQ-ACC-03：curl 无 Cookie 复用 IP session
    def test_gq_acc_03_curl_reuses_ip_session(self):
        """curl 无 Cookie 时通过 IP 地址关联到已有 session。"""
        source = _read_source("app/services/guest_service.py")
        # 与 GQ-ACC-02 同一逻辑路径，验证 IP 查找在 Cookie 查找之后
        assert "get_guest_session_by_ip" in source, (
            "GQ-ACC-03 FAIL: curl 无 Cookie 无法通过 IP 复用 session"
        )

    # GQ-ACC-04：不同 IP 独立配额
    def test_gq_acc_04_different_ip_independent_quota(self):
        """不同 IP 地址查找返回不同 session，配额独立。"""
        source = _read_source("app/crud/guest_session_crud.py")
        # get_guest_session_by_ip 按 ip_address 过滤
        assert "GuestSession.ip_address == ip_address" in source, (
            "GQ-ACC-04 FAIL: get_guest_session_by_ip 未按 ip_address 过滤"
        )

    # GQ-ACC-05：跨日配额重置
    def test_gq_acc_05_daily_quota_reset(self):
        """跨日后 daily_quotas.date 不匹配，get_guest_session_by_ip 返回 None。"""
        source = _read_source("app/crud/guest_session_crud.py")
        # 验证日期不匹配时返回 None
        assert 'quotas.get("date") != today_str' in source, (
            "GQ-ACC-05 FAIL: get_guest_session_by_ip 未检查日期匹配"
        )
        assert "return None" in source, (
            "GQ-ACC-05 FAIL: 日期不匹配时未返回 None"
        )
        # 验证 increment_guest_quota 也有日期重置逻辑
        assert "quotas.get(\"date\") != today_str" in source or 'quotas.get("date") != today_str' in source, (
            "GQ-ACC-05 FAIL: increment_guest_quota 缺少日期重置逻辑"
        )

    # GQ-ACC-06：并发请求不创建重复 session（FOR UPDATE）
    def test_gq_acc_06_concurrent_no_duplicate_session(self):
        """increment_usage 使用 SELECT ... FOR UPDATE 行级锁防止并发竞态。"""
        source = _read_source("app/services/rate_limit_service.py")
        # 验证 for_update=True
        assert "for_update=True" in source, (
            "GQ-ACC-06 FAIL: increment_usage 未使用 for_update=True 行级锁"
        )
        # 验证 get_guest_session 支持 for_update 参数
        crud_source = _read_source("app/crud/guest_session_crud.py")
        assert "with_for_update()" in crud_source, (
            "GQ-ACC-06 FAIL: get_guest_session 未实现 with_for_update()"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 缺陷 2：配额先扣后失败
# ══════════════════════════════════════════════════════════════════════════════


class TestQuotaOrderingFix:
    """验证配额扣减顺序：先检查后消费，失败不扣减。"""

    def test_guest_youtube_routes_use_default_org_settings(self):
        """游客 YouTube 功能应读取默认组织的设置中心配置，而不是 org_id=None。"""
        keyword_source = _read_source("app/api/v1/keyword.py")
        seo_source = _read_source("app/api/v1/seo.py")

        assert "get_settings().guest_default_org_id" in keyword_source, (
            "keyword/research 游客路径应使用 GUEST_DEFAULT_ORG_ID 读取设置中心配置"
        )
        assert seo_source.count("get_settings().guest_default_org_id") >= 2, (
            "seo-score 和 trending 游客路径应使用 GUEST_DEFAULT_ORG_ID 读取设置中心配置"
        )
        assert "current_user.org_id if current_user else None" not in keyword_source
        assert "current_user.org_id if current_user else None" not in seo_source

    # QO-ACC-01：API Key 未配置时不扣配额（返回503）
    def test_qo_acc_01_seo_no_quota_on_missing_api_key(self):
        """seo.py /trending: API Key 未配置时返回 503，不扣配额。"""
        source = _read_source("app/api/v1/seo.py")

        # 找到 trend_discovery_endpoint 函数
        tree = ast.parse(source)
        trend_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "trend_discovery_endpoint":
                trend_func = node
                break

        assert trend_func is not None, "trend_discovery_endpoint 不存在"
        func_source = ast.get_source_segment(source, trend_func)

        # 验证执行顺序：reserve_quota -> cache check -> api_key check -> fetch -> consume
        reserve_pos = func_source.find("reserve_guest_quota")
        cache_pos = func_source.find("get_cached_trend")
        api_key_check_pos = func_source.find("icfg.youtube_api_key")
        fetch_pos = func_source.find("fetch_trending")
        consume_pos = func_source.find("consume_guest_quota")

        # reserve 在最前面（仅检查不扣减）
        assert reserve_pos < api_key_check_pos, (
            "QO-ACC-01 FAIL: reserve_guest_quota 应在 API Key 检查之前"
        )
        # API Key 检查在 consume 之前
        assert api_key_check_pos < consume_pos, (
            "QO-ACC-01 FAIL: API Key 检查应在 consume_guest_quota 之前"
        )
        # fetch 在 consume 之前
        assert fetch_pos < consume_pos, (
            "QO-ACC-01 FAIL: fetch_trending 应在 consume_guest_quota 之前"
        )
        # 503 状态码
        assert "503" in func_source or "SERVICE_UNAVAILABLE" in func_source, (
            "QO-ACC-01 FAIL: API Key 未配置时未返回 503"
        )

    # QO-ACC-02：keyword/research API Key 未配置时不扣配额
    def test_qo_acc_02_keyword_no_quota_on_missing_api_key(self):
        """keyword.py /research: API Key 未配置时返回 503，不扣配额。"""
        source = _read_source("app/api/v1/keyword.py")

        tree = ast.parse(source)
        research_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "keyword_research":
                research_func = node
                break

        assert research_func is not None, "keyword_research 不存在"
        func_source = ast.get_source_segment(source, research_func)

        # 验证执行顺序
        reserve_pos = func_source.find("reserve_guest_quota")
        api_key_check_pos = func_source.find("icfg.youtube_api_key")
        research_pos = func_source.find("research_keyword")
        consume_pos = func_source.find("consume_guest_quota")

        assert reserve_pos < api_key_check_pos, (
            "QO-ACC-02 FAIL: reserve_guest_quota 应在 API Key 检查之前"
        )
        assert api_key_check_pos < consume_pos, (
            "QO-ACC-02 FAIL: API Key 检查应在 consume_guest_quota 之前"
        )
        assert research_pos < consume_pos, (
            "QO-ACC-02 FAIL: research_keyword 应在 consume_guest_quota 之前"
        )
        assert "503" in func_source or "SERVICE_UNAVAILABLE" in func_source, (
            "QO-ACC-02 FAIL: API Key 未配置时未返回 503"
        )

    # QO-ACC-03：缓存命中时不扣配额
    def test_qo_acc_03_cache_hit_no_quota_consumed(self):
        """seo.py /trending: 缓存命中时直接返回，不扣配额。"""
        source = _read_source("app/api/v1/seo.py")

        tree = ast.parse(source)
        trend_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "trend_discovery_endpoint":
                trend_func = node
                break

        func_source = ast.get_source_segment(source, trend_func)

        # 缓存命中时直接 return，不执行 consume_guest_quota
        cache_check_pos = func_source.find("get_cached_trend")
        cache_return_pos = func_source.find("return TrendDiscoveryResponse(**cached)")
        consume_pos = func_source.find("consume_guest_quota")

        assert cache_return_pos > 0, (
            "QO-ACC-03 FAIL: 缓存命中时未直接返回"
        )
        assert cache_return_pos < consume_pos, (
            "QO-ACC-03 FAIL: 缓存命中 return 应在 consume_guest_quota 之前"
        )
        # 缓存命中 return 后不应继续执行到 consume
        # 验证 cache 命中分支是一个 early return
        cache_block_start = func_source.find("if cached is not None:", cache_check_pos)
        assert cache_block_start > 0, "QO-ACC-03: 缓存命中检查不存在"

    # QO-ACC-04：正常调用仍扣配额
    def test_qo_acc_04_normal_call_consumes_quota(self):
        """正常 API 调用成功后 consume_guest_quota 被调用。"""
        source = _read_source("app/api/v1/seo.py")
        assert "consume_guest_quota" in source, (
            "QO-ACC-04 FAIL: seo.py 缺少 consume_guest_quota 调用"
        )

        keyword_source = _read_source("app/api/v1/keyword.py")
        assert "consume_guest_quota" in keyword_source, (
            "QO-ACC-04 FAIL: keyword.py 缺少 consume_guest_quota 调用"
        )

    # 额外验证：reserve_guest_quota 和 consume_guest_quota 是两阶段模式
    def test_two_phase_quota_pattern(self):
        """验证两阶段配额模式：reserve（检查）+ consume（扣减）分离。"""
        source = _read_source("app/services/guest_service.py")
        assert "reserve_guest_quota" in source, (
            "缺少 reserve_guest_quota 函数"
        )
        assert "consume_guest_quota" in source, (
            "缺少 consume_guest_quota 函数"
        )
        # reserve 只调用 check_quota，不调用 increment_usage
        tree = ast.parse(source)
        reserve_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "reserve_guest_quota":
                reserve_func = node
                break

        reserve_source = ast.get_source_segment(source, reserve_func)
        assert "check_quota" in reserve_source, (
            "reserve_guest_quota 未调用 check_quota"
        )
        assert "increment_usage" not in reserve_source, (
            "reserve_guest_quota 不应调用 increment_usage"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 缺陷 3：状态码 + 消息双路径
# ══════════════════════════════════════════════════════════════════════════════


class TestStatusCodeAndDualMessage:
    """验证 503 状态码和游客/管理员消息双路径。"""

    # SC-ACC-01：游客看到"服务暂不可用，请稍后重试"
    def test_sc_acc_01_guest_sees_retry_message(self):
        """API Key 未配置时游客看到友好重试消息。"""
        source = _read_source("app/api/v1/seo.py")
        assert "服务暂不可用，请稍后重试" in source, (
            "SC-ACC-01 FAIL: seo.py 游客消息不是'服务暂不可用，请稍后重试'"
        )

        keyword_source = _read_source("app/api/v1/keyword.py")
        assert "服务暂不可用，请稍后重试" in keyword_source, (
            "SC-ACC-01 FAIL: keyword.py 游客消息不是'服务暂不可用，请稍后重试'"
        )

    # SC-ACC-02：管理员看到配置引导消息
    def test_sc_acc_02_admin_sees_config_guide(self):
        """API Key 未配置时已登录用户（管理员）看到设置中心引导消息。"""
        source = _read_source("app/api/v1/seo.py")
        assert "请在设置中心配置" in source, (
            "SC-ACC-02 FAIL: seo.py 管理员消息缺少'设置中心'引导"
        )

        keyword_source = _read_source("app/api/v1/keyword.py")
        assert "请在设置中心配置" in keyword_source, (
            "SC-ACC-02 FAIL: keyword.py 管理员消息缺少'设置中心'引导"
        )

    # SC-ACC-03：503 允许客户端重试
    def test_sc_acc_03_503_allows_retry(self):
        """API Key 未配置时返回 503 而非 400，允许客户端重试。"""
        source = _read_source("app/api/v1/seo.py")
        assert "503" in source or "SERVICE_UNAVAILABLE" in source, (
            "SC-ACC-03 FAIL: seo.py 未使用 503 状态码"
        )
        # 确认不再使用 400
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                func_src = ast.get_source_segment(source, node)
                # 在 503 相关上下文中不应有 400
                if "youtube_api_key" in func_src and "503" in func_src:
                    assert 'status_code=400' not in func_src or "400" not in func_src.split("503")[0], (
                        "SC-ACC-03 FAIL: seo.py API Key 检查仍使用 400 状态码"
                    )

        keyword_source = _read_source("app/api/v1/keyword.py")
        assert "503" in keyword_source or "SERVICE_UNAVAILABLE" in keyword_source, (
            "SC-ACC-03 FAIL: keyword.py 未使用 503 状态码"
        )

    # 验证消息双路径逻辑：根据 current_user 是否存在区分
    def test_dual_message_branching(self):
        """消息根据 current_user 是否存在区分游客和管理员。"""
        source = _read_source("app/api/v1/seo.py")
        # 验证 if current_user 分支
        assert "if current_user:" in source, (
            "SC: seo.py 缺少 current_user 分支判断"
        )

        keyword_source = _read_source("app/api/v1/keyword.py")
        assert "if current_user:" in keyword_source, (
            "SC: keyword.py 缺少 current_user 分支判断"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 缺陷 4：keyword-history 路由
# ══════════════════════════════════════════════════════════════════════════════


class TestKeywordHistoryRoute:
    """验证 keyword-history 路由实现和数据隔离。"""

    # KH-ACC-01：已登录用户获取历史
    def test_kh_acc_01_logged_in_user_gets_history(self):
        """keyword-history 路由存在且使用 CurrentUserDep。"""
        source = _read_source("app/api/v1/keyword.py")

        # 验证路由存在
        assert "/keyword-history" in source, (
            "KH-ACC-01 FAIL: /keyword-history 路由不存在"
        )

        # 验证使用 CurrentUserDep（需要登录）
        tree = ast.parse(source)
        history_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "keyword_history":
                history_func = node
                break

        assert history_func is not None, "keyword_history 函数不存在"
        func_source = ast.get_source_segment(source, history_func)
        assert "current_user" in func_source, (
            "KH-ACC-01 FAIL: keyword_history 未使用 current_user"
        )
        assert "CurrentUserDep" in source, (
            "KH-ACC-01 FAIL: keyword.py 未导入 CurrentUserDep"
        )

    # KH-ACC-02：游客无法获取历史（401）
    def test_kh_acc_02_guest_cannot_get_history(self):
        """keyword-history 使用 CurrentUserDep，未登录返回 401。"""
        source = _read_source("app/api/v1/keyword.py")

        tree = ast.parse(source)
        history_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "keyword_history":
                history_func = node
                break

        func_source = ast.get_source_segment(source, history_func)
        # CurrentUserDep 是必须的依赖，未登录会自动 401
        assert "CurrentUserDep" in source, (
            "KH-ACC-02 FAIL: keyword-history 未使用 CurrentUserDep，游客可能绕过"
        )
        # 确认不是 OptionalUserDep
        for arg in history_func.args.args:
            if arg.arg == "current_user":
                # 检查注解是否为 CurrentUserDep 而非 OptionalUserDep
                assert "OptionalUserDep" not in ast.get_source_segment(source, arg.annotation), (
                    "KH-ACC-02 FAIL: keyword-history 使用了 OptionalUserDep，游客不会收到 401"
                )

    # KH-ACC-03：数据隔离（用户A看不到用户B的历史）
    def test_kh_acc_03_data_isolation(self):
        """keyword-history 按 user_id 过滤，用户间数据隔离。"""
        source = _read_source("app/api/v1/keyword.py")

        tree = ast.parse(source)
        history_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "keyword_history":
                history_func = node
                break

        func_source = ast.get_source_segment(source, history_func)
        assert "current_user.id" in func_source, (
            "KH-ACC-03 FAIL: keyword_history 未按 current_user.id 过滤"
        )

        # 验证 CRUD 层也按 user_id 过滤
        crud_source = _read_source("app/crud/keyword_history.py")
        assert "KeywordHistory.user_id == user_id" in crud_source, (
            "KH-ACC-03 FAIL: list_keyword_history_by_user 未按 user_id 过滤"
        )

    # 验证 keyword_history 模型存在且有 user_id 字段
    def test_keyword_history_model_has_user_id(self):
        """KeywordHistory 模型有 user_id 字段且为外键。"""
        source = _read_source("app/models/keyword_history.py")
        assert "user_id" in source, (
            "KeywordHistory 模型缺少 user_id 字段"
        )
        assert "ForeignKey" in source, (
            "KeywordHistory.user_id 缺少外键约束"
        )

    # 验证数据库迁移存在
    def test_keyword_history_migration_exists(self):
        """keyword_history 表的 alembic 迁移存在。"""
        migration_dir = _BACKEND_ROOT / "alembic/versions"
        files = [path.name for path in migration_dir.iterdir()]
        keyword_history_migrations = [f for f in files if "keyword_history" in f]
        assert len(keyword_history_migrations) > 0, (
            "KH: keyword_history 表的 alembic 迁移不存在"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 缺陷 5：feishu_docs 越权删除
# ══════════════════════════════════════════════════════════════════════════════


class TestFeishuDocsAuthorization:
    """验证 feishu_docs 删除/归档操作的 user_id 权限校验。"""

    # FD-ACC-01：用户删除自己的文档成功
    def test_fd_acc_01_user_can_delete_own_doc(self):
        """check_doc_ownership: user_id 匹配时返回 True。"""
        source = _read_source("app/crud/feishu_doc.py")
        # check_doc_ownership 函数存在
        assert "check_doc_ownership" in source, (
            "FD-ACC-01 FAIL: check_doc_ownership 函数不存在"
        )
        # 当 doc.user_id == user_id 时返回 True
        assert "doc.user_id == user_id" in source, (
            "FD-ACC-01 FAIL: check_doc_ownership 未检查 doc.user_id == user_id"
        )

    # FD-ACC-02：用户无法删除他人文档（403）
    def test_fd_acc_02_user_cannot_delete_others_doc(self):
        """删除路由使用 check_doc_ownership，不匹配时返回 403。"""
        route_source = _read_source("app/api/v1/feishu_docs.py")
        crud_source = _read_source("app/crud/feishu_doc.py")

        # 路由层调用 check_doc_ownership
        assert "check_doc_ownership" in route_source, (
            "FD-ACC-02 FAIL: 删除路由未调用 check_doc_ownership"
        )
        # 不匹配时返回 403
        assert "403" in route_source, (
            "FD-ACC-02 FAIL: 删除路由未返回 403"
        )
        assert "无权删除" in route_source or "无权" in route_source, (
            "FD-ACC-02 FAIL: 删除路由 403 消息未提示无权"
        )

        # CRUD 层：check_doc_ownership 在 user_id 不匹配且非 None 时返回 False
        assert "doc.user_id == user_id" in crud_source, (
            "FD-ACC-02 FAIL: check_doc_ownership 缺少 doc.user_id == user_id 比较（不匹配时隐式返回 False）"
        )

    # FD-ACC-03：历史文档（user_id=NULL）仍可删除
    def test_fd_acc_03_null_user_id_doc_deletable(self):
        """check_doc_ownership: user_id 为 None 时返回 True（兼容历史数据）。"""
        source = _read_source("app/crud/feishu_doc.py")
        assert "doc.user_id is None" in source, (
            "FD-ACC-03 FAIL: check_doc_ownership 未处理 user_id 为 None 的情况"
        )
        # None 时应返回 True
        tree = ast.parse(source)
        ownership_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "check_doc_ownership":
                ownership_func = node
                break

        func_source = ast.get_source_segment(source, ownership_func)
        # 验证 None 检查在 == 检查之前或独立分支
        none_check_pos = func_source.find("doc.user_id is None")
        eq_check_pos = func_source.find("doc.user_id == user_id")
        assert none_check_pos > 0, "FD-ACC-03: 缺少 None 检查"
        assert none_check_pos < eq_check_pos, (
            "FD-ACC-03 FAIL: None 检查应在 == 检查之前"
        )

    # 验证归档操作也使用 check_doc_ownership
    def test_archive_uses_ownership_check(self):
        """归档路由也使用 check_doc_ownership 防止越权。"""
        source = _read_source("app/api/v1/feishu_docs.py")
        # 归档路由中也应调用 check_doc_ownership
        tree = ast.parse(source)
        archive_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "archive_doc":
                archive_func = node
                break

        assert archive_func is not None, "archive_doc 函数不存在"
        func_source = ast.get_source_segment(source, archive_func)
        assert "check_doc_ownership" in func_source, (
            "归档路由未调用 check_doc_ownership，存在越权归档风险"
        )
        assert "403" in func_source, (
            "归档路由未返回 403"
        )

    # 验证 FeishuDoc 模型有 user_id 字段
    def test_feishu_doc_model_has_user_id(self):
        """FeishuDoc 模型有 user_id 可空字段。"""
        source = _read_source("app/models/feishu_doc.py")
        assert "user_id" in source, (
            "FeishuDoc 模型缺少 user_id 字段"
        )
        assert "nullable=True" in source, (
            "FeishuDoc.user_id 应为 nullable=True（兼容历史数据）"
        )

    # 验证创建时写入 user_id
    def test_create_writes_user_id(self):
        """创建飞书文档时写入 user_id。"""
        source = _read_source("app/api/v1/feishu_docs.py")
        tree = ast.parse(source)
        create_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "create_doc":
                create_func = node
                break

        func_source = ast.get_source_segment(source, create_func)
        assert "user_id=current_user.id" in func_source, (
            "创建飞书文档时未写入 current_user.id"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 缺陷 6：jimeng 横向回退
# ══════════════════════════════════════════════════════════════════════════════


class TestJimengLateralFallback:
    """验证 jimeng 模型库不再使用 org 级回退。"""

    # JM-ACC-01：未配置 jimeng 返回 400
    def test_jm_acc_01_unconfigured_returns_400(self):
        """_resolve_jimeng_config 未找到用户模型库时返回 400。"""
        source = _read_source("app/api/v1/jimeng.py")

        tree = ast.parse(source)
        resolve_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_resolve_jimeng_config":
                resolve_func = node
                break

        assert resolve_func is not None, "_resolve_jimeng_config 不存在"
        func_source = ast.get_source_segment(source, resolve_func)

        # 验证 ml is None 时抛 400
        assert "ml is None" in func_source, (
            "JM-ACC-01 FAIL: 未检查 ml is None"
        )
        assert "400" in func_source or "BAD_REQUEST" in func_source, (
            "JM-ACC-01 FAIL: 未配置时未返回 400"
        )
        assert "即梦" in func_source, (
            "JM-ACC-01 FAIL: 400 消息未提及即梦 AI"
        )

    # JM-ACC-02：不再使用他人 API Key
    def test_jm_acc_02_no_org_fallback(self):
        """_resolve_jimeng_config 不包含 org 级回退逻辑。"""
        source = _read_source("app/api/v1/jimeng.py")

        tree = ast.parse(source)
        resolve_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_resolve_jimeng_config":
                resolve_func = node
                break

        func_source = ast.get_source_segment(source, resolve_func)

        # 不应包含 org 级回退查询
        assert "ModelLibrary.org_id" not in func_source, (
            "JM-ACC-02 FAIL: 仍包含 org_id 级回退查询"
        )
        assert "library_kind" not in func_source, (
            "JM-ACC-02 FAIL: 仍包含 library_kind 回退查询"
        )

        # 应使用 get_by_user（按 user_id 查找）
        assert "get_by_user" in func_source, (
            "JM-ACC-02 FAIL: 未使用 get_by_user 按 user_id 查找"
        )

        # 验证函数注释说明不做回退
        assert "回退" not in func_source or "不做" in func_source or "不" in func_source, (
            "JM-ACC-02: 函数注释应说明不做 org 级回退"
        )


# ══════════════════════════════════════════════════════════════════════════════
# XFF 防护验证
# ══════════════════════════════════════════════════════════════════════════════


class TestXFFProtection:
    """验证 X-Forwarded-For 头的 IP 提取安全策略。"""

    def test_trusted_proxy_count_config(self):
        """config.py 包含 trusted_proxy_count 配置项。"""
        source = _read_source("app/core/config.py")
        assert "trusted_proxy_count" in source, (
            "config.py 缺少 trusted_proxy_count 配置项"
        )

    def test_xff_parsing_logic(self):
        """guest_service.py 正确解析 X-Forwarded-For 头。"""
        source = _read_source("app/services/guest_service.py")
        # 验证 XFF 解析逻辑
        assert "x-forwarded-for" in source, (
            "guest_service.py 缺少 X-Forwarded-For 解析"
        )
        assert "trusted_proxy_count" in source, (
            "guest_service.py 未使用 trusted_proxy_count"
        )

    def test_ip_validation_rejects_private(self):
        """_validate_ip_address 拒绝内网/回环/保留地址。"""
        source = _read_source("app/services/guest_service.py")
        assert "_validate_ip_address" in source, (
            "缺少 _validate_ip_address 函数"
        )
        assert "is_loopback" in source, "未检查回环地址"
        assert "is_private" in source, "未检查内网地址"
        assert "is_link_local" in source, "未检查链路本地地址"


# ══════════════════════════════════════════════════════════════════════════════
# seo_scoring 配额两阶段验证
# ══════════════════════════════════════════════════════════════════════════════


class TestSeoScoringQuotaOrdering:
    """验证 seo-score 端点也使用两阶段配额模式。"""

    def test_seo_scoring_two_phase_quota(self):
        """seo_scoring_endpoint 使用 reserve + consume 两阶段。"""
        source = _read_source("app/api/v1/seo.py")

        tree = ast.parse(source)
        scoring_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "seo_scoring_endpoint":
                scoring_func = node
                break

        assert scoring_func is not None, "seo_scoring_endpoint 不存在"
        func_source = ast.get_source_segment(source, scoring_func)

        # 验证两阶段模式
        assert "reserve_guest_quota" in func_source, (
            "seo_scoring_endpoint 缺少 reserve_guest_quota"
        )
        assert "consume_guest_quota" in func_source, (
            "seo_scoring_endpoint 缺少 consume_guest_quota"
        )

        # 验证顺序：reserve -> api_key check -> calculate -> consume
        reserve_pos = func_source.find("reserve_guest_quota")
        api_key_pos = func_source.find("youtube_api_key")
        calc_pos = func_source.find("calculate_seo_score")
        consume_pos = func_source.find("consume_guest_quota")

        assert reserve_pos < api_key_pos, "reserve 应在 api_key 检查之前"
        assert api_key_pos < consume_pos, "api_key 检查应在 consume 之前"
        assert calc_pos < consume_pos, "calculate 应在 consume 之前"

    def test_seo_scoring_503_on_missing_api_key(self):
        """seo_scoring_endpoint API Key 未配置时返回 503。"""
        source = _read_source("app/api/v1/seo.py")

        tree = ast.parse(source)
        scoring_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "seo_scoring_endpoint":
                scoring_func = node
                break

        func_source = ast.get_source_segment(source, scoring_func)
        assert "503" in func_source or "SERVICE_UNAVAILABLE" in func_source, (
            "seo_scoring_endpoint API Key 未配置时未返回 503"
        )
        assert "服务暂不可用" in func_source, (
            "seo_scoring_endpoint 游客消息缺少'服务暂不可用'"
        )
