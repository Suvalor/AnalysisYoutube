from fastapi import APIRouter, HTTPException, status

from alibabacloud_sts20150401.client import Client as StsClient
from alibabacloud_sts20150401 import models as sts_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.exceptions import ClientException as TeaClientException

from app.api.deps import CurrentUserDep, DBSessionDep
from app.services.config_manager import resolve_integration_config


router = APIRouter()


@router.get("/sts-token")
async def get_sts_token(db: DBSessionDep, current_user: CurrentUserDep) -> dict:
    cfg = await resolve_integration_config(db, org_id=current_user.org_id)
    required_values = [
        cfg.aliyun_access_key_id,
        cfg.aliyun_access_key_secret,
        cfg.aliyun_role_arn,
        cfg.aliyun_region_id,
        cfg.aliyun_oss_bucket_name,
        cfg.aliyun_oss_endpoint,
    ]
    if not all(required_values):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="阿里云 OSS 配置不完整",
        )

    config = open_api_models.Config(
        access_key_id=cfg.aliyun_access_key_id,
        access_key_secret=cfg.aliyun_access_key_secret,
        endpoint=f"sts.{cfg.aliyun_region_id}.aliyuncs.com",
    )
    client = StsClient(config)
    req = sts_models.AssumeRoleRequest(
        role_arn=cfg.aliyun_role_arn,
        role_session_name="creator-saas-oss-upload",
        duration_seconds=3600,
    )
    try:
        resp = client.assume_role(req)
    except TeaClientException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"阿里云 STS 调用失败: {exc}",
        )
    cred = resp.body.credentials
    if cred is None:
        raise HTTPException(status_code=500, detail="获取 STS 凭证失败")

    custom = (cfg.aliyun_custom_domain or "").strip().rstrip("/")
    endpoint = cfg.aliyun_oss_endpoint
    bucket = cfg.aliyun_oss_bucket_name
    if custom:
        public_access_base = custom
    elif endpoint.startswith("http://") or endpoint.startswith("https://"):
        public_access_base = endpoint.rstrip("/")
    else:
        public_access_base = f"https://{bucket}.{endpoint}".rstrip("/")

    return {
        "AccessKeyId": cred.access_key_id,
        "AccessKeySecret": cred.access_key_secret,
        "SecurityToken": cred.security_token,
        "Expiration": cred.expiration,
        "region": cfg.aliyun_region_id,
        "bucket": cfg.aliyun_oss_bucket_name,
        "endpoint": cfg.aliyun_oss_endpoint,
        "public_access_base": public_access_base,
    }

