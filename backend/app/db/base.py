from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy Declarative 基类。"""

    pass


# 导入模型以便 Alembic 自动发现元数据
from app.models.user import User  # noqa: F401,E402

