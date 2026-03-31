from app.db.base_class import Base


# 导入模型以便 Alembic 自动发现元数据
from app.models.user import User  # noqa: F401,E402
from app.models.yt_channel import YtChannel  # noqa: F401,E402
from app.models.youtube import YouTubeChannel, UserCompetitorPool, YouTubeVideo  # noqa: F401,E402

