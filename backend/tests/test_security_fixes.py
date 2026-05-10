"""安全修复验证测试。"""

import pytest


class TestConfigSecurity:
    """config.py 安全默认值验证。"""

    _VALID_SECRET_KEY = "a" * 32  # 满足 SECRET_KEY 最少 32 字符校验

    def test_secret_key_default_empty(self):
        """SECRET_KEY 默认值应为空字符串，不应为弱值。"""
        from app.core.config import Settings
        s = Settings(
            MYSQL_PASSWORD="test",
            SECRET_KEY=self._VALID_SECRET_KEY,
            DATABASE_URL="mysql+asyncmy://test:test@localhost/test",
        )
        assert s.secret_key == self._VALID_SECRET_KEY
        # 验证 Field 默认值：不传 SECRET_KEY 时应从环境变量读取（由 conftest.py 设置）
        # Field 定义中默认值为空字符串 ""
        from unittest.mock import patch
        with patch.dict("os.environ", {}, clear=False):
            # 移除环境变量后，SECRET_KEY 应回退到 Field 默认值 ""
            # 但 model_validator 会拒绝空值，因此验证 Field 定义本身
            import inspect
            field_info = Settings.model_fields["secret_key"]
            assert field_info.default == "", "SECRET_KEY Field 默认值应为空字符串"

    def test_mysql_password_default_empty(self):
        """mysql_password 默认值应为空字符串。"""
        from app.core.config import Settings
        # 验证 Field 定义中默认值为空字符串（而非运行时从环境变量读取的值）
        field_info = Settings.model_fields["mysql_password"]
        assert field_info.default == "", "mysql_password Field 默认值应为空字符串"


class TestDockerComposeSecurity:
    """docker-compose.yml 密钥外移验证。"""

    # 曾泄露的真实密钥值（已从仓库移除，此处用于确认不会回归）
    _KNOWN_LEAKED_SECRETS: list[tuple[str, str]] = [
        ("literal:REDACTED_SECRET_KEY", "JWT SECRET_KEY"),
        ("literal:REDACTED_SMTP_PASSWORD", "SMTP_PASSWORD"),
        ("literal:REDACTED_SMTP_USER", "SMTP_USER"),
        ("literal:REDACTED_SMTP_EMAIL", "SMTP_FROM_EMAIL"),
        ("literal:REDACTED_DOMAIN", "FRONTEND_BASE_URL domain"),
        ("literal:REDACTED_MYSQL_PASSWORD", "MYSQL_PASSWORD"),
        ("literal:REDACTED_SMTP_HOST", "SMTP_HOST"),
    ]

    # API Key 前缀模式
    _API_KEY_PREFIXES: list[tuple[str, str]] = [
        ("AIzaSy", "YouTube API Key"),
        ("LTAI5t", "阿里云 AccessKey ID"),
    ]

    def test_no_hardcoded_secrets(self):
        """docker-compose.yml 中不应包含曾泄露的真实密钥值。"""
        import pathlib
        compose_path = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"
        if not compose_path.exists():
            pytest.skip("docker-compose.yml 不存在")
        content = compose_path.read_text()
        for secret, desc in self._KNOWN_LEAKED_SECRETS:
            assert secret not in content, f"docker-compose.yml 中不应包含 {desc} 明文"

    def test_no_hardcoded_api_key_prefixes(self):
        """docker-compose.yml 中不应包含 API Key 前缀明文。"""
        import pathlib
        compose_path = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"
        if not compose_path.exists():
            pytest.skip("docker-compose.yml 不存在")
        content = compose_path.read_text()
        for prefix, desc in self._API_KEY_PREFIXES:
            assert prefix not in content, f"docker-compose.yml 中不应包含 {desc} 前缀明文"

    def test_sensitive_vars_use_env_refs(self):
        """docker-compose.yml 中的敏感变量应使用 ${VAR} 环境变量引用。"""
        import pathlib
        compose_path = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"
        if not compose_path.exists():
            pytest.skip("docker-compose.yml 不存在")
        content = compose_path.read_text()
        # 以下变量必须使用环境变量引用（不允许明文）
        required_env_refs = [
            "MYSQL_ROOT_PASSWORD",
            "MYSQL_PASSWORD",
            "SECRET_KEY",
            "SMTP_HOST",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "SMTP_FROM_EMAIL",
            "FRONTEND_BASE_URL",
        ]
        for var in required_env_refs:
            assert "${" + var in content, f"docker-compose.yml 中 {var} 应使用环境变量引用 ${var}"

    def test_no_plain_password_in_healthcheck(self):
        """MySQL healthcheck 不应包含明文密码。"""
        import pathlib
        compose_path = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"
        if not compose_path.exists():
            pytest.skip("docker-compose.yml 不存在")
        content = compose_path.read_text()
        # healthcheck 中 -p 参数应使用环境变量引用
        assert "-proot" not in content, "healthcheck 不应包含 -proot 明文密码"
        assert "-p${" in content or "-p$" in content, "healthcheck 应使用环境变量引用密码"


class TestHttpxTrustEnv:
    """httpx trust_env=False 验证。"""

    def test_youtube_service_trust_env(self):
        """youtube_service.py 中所有 httpx.AsyncClient 应设置 trust_env=False。"""
        import pathlib
        svc_path = pathlib.Path(__file__).resolve().parents[1] / "app" / "services" / "youtube_service.py"
        if not svc_path.exists():
            pytest.skip("youtube_service.py 不存在")
        content = svc_path.read_text()
        # 统计 AsyncClient 调用数和 trust_env=False 数
        import re
        client_calls = re.findall(r"httpx\.AsyncClient\(", content)
        trust_env_calls = re.findall(r"trust_env=False", content)
        assert len(client_calls) == len(trust_env_calls), (
            f"httpx.AsyncClient 调用数({len(client_calls)}) 与 trust_env=False 数({len(trust_env_calls)}) 不匹配"
        )
