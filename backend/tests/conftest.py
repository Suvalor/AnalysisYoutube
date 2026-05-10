"""
测试环境配置 — 在任何测试模块导入前设置环境变量，
避免 app.core.config 模块级 settings 实例化因缺少 SECRET_KEY 而失败。
"""

import os

# 必须在 import app 之前设置，否则 config.py 模块级 get_settings() 会失败
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-min-32chars")
os.environ.setdefault("MYSQL_USER", "test")
os.environ.setdefault("MYSQL_PASSWORD", "test")
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_DB", "test_db")
