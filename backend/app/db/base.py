from app.db.base_class import Base


# 导入模型以便 Alembic 自动发现元数据
from app.models.user import User  # noqa: F401,E402
from app.models.yt_channel import YtChannel  # noqa: F401,E402
from app.models.library import AssetLibrary, ModelLibrary, PromptLibrary, ScriptLibrary, StyleLibrary  # noqa: F401,E402
from app.models.video_project import VideoProject  # noqa: F401,E402
from app.models.inspiration import Inspiration  # noqa: F401,E402
from app.models.sop import SopAsset, SopMedia, SopScript, SopSegment, SopShot  # noqa: F401,E402
from app.models.quota import ApiQuotaUsage  # noqa: F401,E402
from app.models.youtube import (  # noqa: F401,E402
    YouTubeChannel,
    YouTubeChannelHistory,
    YouTubeChannelInsight,
    UserCompetitorPool,
    YouTubeComment,
    YouTubeVideo,
)

