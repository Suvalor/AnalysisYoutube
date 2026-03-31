from fastapi import APIRouter, HTTPException, status

from alibabacloud_sts20150401.client import Client as StsClient
from alibabacloud_sts20150401 import models as sts_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.exceptions import ClientException as TeaClientException

from app.api.deps import CurrentUserDep
from app.core.config import settings


router = APIRouter()


@router.get("/sts-token")
async def get_sts_token(_: CurrentUserDep) -> dict:
    required_values = [
        settings.aliyun_access_key_id,
        settings.aliyun_access_key_secret,
        settings.aliyun_role_arn,
        settings.aliyun_region_id,
        settings.aliyun_oss_bucket_name,
        settings.aliyun_oss_endpoint,
    ]
    if not all(required_values):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="阿里云 OSS 配置不完整",
        )

    config = open_api_models.Config(
        access_key_id=settings.aliyun_access_key_id,
        access_key_secret=settings.aliyun_access_key_secret,
        endpoint=f"sts.{settings.aliyun_region_id}.aliyuncs.com",
    )
    client = StsClient(config)
    req = sts_models.AssumeRoleRequest(
        role_arn=settings.aliyun_role_arn,
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

    return {
        "AccessKeyId": cred.access_key_id,
        "AccessKeySecret": cred.access_key_secret,
        "SecurityToken": cred.security_token,
        "Expiration": cred.expiration,
        "region": settings.aliyun_region_id,
        "bucket": settings.aliyun_oss_bucket_name,
        "endpoint": settings.aliyun_oss_endpoint,
    }

