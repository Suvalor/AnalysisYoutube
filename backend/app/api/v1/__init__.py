from fastapi import APIRouter

from app.api.v1 import ai
from app.api.v1 import asset_library
from app.api.v1 import auth
from app.api.v1 import inspiration
from app.api.v1 import integration_settings
from app.api.v1 import jimeng
from app.api.v1 import knowledge_base
from app.api.v1 import materials
from app.api.v1 import model_library
from app.api.v1 import feishu_docs
from app.api.v1 import oss
from app.api.v1 import prompt_library
from app.api.v1 import scripts
from app.api.v1 import script_library
from app.api.v1 import sop
from app.api.v1 import style_library
from app.api.v1 import users
from app.api.v1 import video_projects
from app.api.v1 import videos
from app.api.v1 import youtube


api_router_v1 = APIRouter()

api_router_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router_v1.include_router(inspiration.router, prefix="/inspirations", tags=["inspirations"])
api_router_v1.include_router(youtube.router, prefix="/youtube", tags=["youtube"])
api_router_v1.include_router(prompt_library.router, prefix="/libraries/prompts", tags=["prompt-library"])
api_router_v1.include_router(style_library.router, prefix="/libraries/styles", tags=["style-library"])
api_router_v1.include_router(model_library.router, prefix="/libraries/models", tags=["model-library"])
api_router_v1.include_router(asset_library.router, prefix="/libraries/assets", tags=["asset-library"])
api_router_v1.include_router(asset_library.router, prefix="/assets", tags=["assets"])
api_router_v1.include_router(script_library.router, prefix="/libraries/scripts", tags=["script-library"])
api_router_v1.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["knowledge-base"])
api_router_v1.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router_v1.include_router(scripts.router, prefix="/v1/scripts", tags=["scripts"])
api_router_v1.include_router(sop.router, prefix="/sop", tags=["sop"])
api_router_v1.include_router(jimeng.router, prefix="/v1/jimeng", tags=["jimeng"])
api_router_v1.include_router(materials.router, prefix="/v1/materials", tags=["materials"])
api_router_v1.include_router(video_projects.router, prefix="/video-projects", tags=["video-projects"])
api_router_v1.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router_v1.include_router(oss.router, prefix="/oss", tags=["oss"])
api_router_v1.include_router(users.router, prefix="/users", tags=["users"])
api_router_v1.include_router(integration_settings.router, prefix="/users", tags=["integration-settings"])
api_router_v1.include_router(feishu_docs.router, prefix="/feishu_docs", tags=["feishu-docs"])

