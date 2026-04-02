"""asset_libraries.source 取值：区分素材入口，供素材库列表过滤。"""

# 设置中心「素材库」手动上传
ASSET_SOURCE_MANUAL = "MANUAL"
# SOP 工作流内上传（仍落库 asset_libraries，但不进素材库主列表）
ASSET_SOURCE_SOP = "SOP"
# 灵感池等通过 /materials/upload 写入
ASSET_SOURCE_INSPIRATION = "INSPIRATION"

ALLOWED_ASSET_SOURCES = frozenset({ASSET_SOURCE_MANUAL, ASSET_SOURCE_SOP, ASSET_SOURCE_INSPIRATION})
