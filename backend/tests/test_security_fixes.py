"""安全修复验证测试。"""

import pytest


class TestConfigSecurity:
    """config.py 安全默认值验证。"""

    def test_secret_key_default_empty(self):
        """SECRET_KEY 默认值应为空字符串，不应为弱值。"""
        from app.core.config import Settings
        s = Settings(
            MYSQL_PASSWORD="test",
            SECRET_KEY="test_key_for_unit_test",
            DATABASE_URL="mysql+asyncmy://test:test@localhost/test",
        )
        # 验证 Field 默认值：不传 SECRET_KEY 时应为空
        s_default = Settings(
            MYSQL_PASSWORD="test",
            DATABASE_URL="mysql+asyncmy://test:test@localhost/test",
        )
        assert s_default.secret_key == "", "SECRET_KEY 默认值应为空字符串"

    def test_mysql_password_default_empty(self):
        """mysql_password 默认值应为空字符串。"""
        from app.core.config import Settings
        s = Settings(
            SECRET_KEY="test",
            DATABASE_URL="mysql+asyncmy://test:test@localhost/test",
        )
        assert s.mysql_password == "", "mysql_password 默认值应为空字符串"


class TestDockerComposeSecurity:
    """docker-compose.yml 密钥外移验证。"""

    def test_no_hardcoded_api_keys(self):
        """docker-compose.yml 中不应包含硬编码的 API 密钥。"""
        import pathlib
        compose_path = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"
        if not compose_path.exists():
            pytest.skip("docker-compose.yml 不存在")
        content = compose_path.read_text()
        # 检查不应出现明文 API Key 模式
        assert "AIzaSy" not in content, "docker-compose.yml 中不应包含 YouTube API Key 明文"
        assert "cb1ae748" not in content, "docker-compose.yml 中不应包含火山引擎 API Key 明文"
        assert "LTAI5t" not in content, "docker-compose.yml 中不应包含阿里云 AK 明文"
        assert "mriIs1I" not in content, "docker-compose.yml 中不应包含阿里云 SK 明文"


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
