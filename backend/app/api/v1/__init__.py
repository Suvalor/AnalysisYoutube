from fastapi import APIRouter

from app.api.v1 import auth
from app.api.v1 import youtube


api_router_v1 = APIRouter()

api_router_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router_v1.include_router(youtube.router, prefix="/youtube", tags=["youtube"])

