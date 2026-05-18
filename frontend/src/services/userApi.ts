import apiClient from "./apiClient";

export type UserSettings = {
  feishu_doc_url: string | null;
  ai_api_base_url: string | null;
  ai_models_json: string | null;
  ai_prompt_config_json: string | null;
  has_ai_api_key: boolean;
  theme: string | null;
  locale: string | null;
};

/** 更新设置；不要传 ai_api_key 字段表示不修改已存密钥 */
export type UserSettingsUpdatePayload = Partial<
  Omit<UserSettings, "has_ai_api_key"> & { ai_api_key?: string }
>;

export async function getUserSettingsApi() {
  const res = await apiClient.get("/api/users/me/settings");
  return res.data as UserSettings;
}

export async function updateUserSettingsApi(payload: UserSettingsUpdatePayload) {
  const res = await apiClient.put("/api/users/me/settings", payload);
  return res.data as UserSettings;
}

/** 组织级集成配置（合并后非密钥 + has_* + display 占位，勿将 display 当密钥提交） */
export type IntegrationSettingsRead = {
  org_id: number;
  org_name: string;
  active_storage_provider: string;
  aliyun_access_key_id: string;
  aliyun_role_arn: string;
  aliyun_region_id: string;
  aliyun_oss_bucket_name: string;
  aliyun_oss_endpoint: string;
  aliyun_custom_domain: string;
  tencent_cos_secret_id: string;
  tencent_cos_region: string;
  tencent_cos_bucket: string;
  tencent_custom_domain: string;
  volc_cv_access_key_id: string;
  volc_cv_region: string;
  volc_cv_host: string;
  volc_cv_inpaint_req_key: string;
  watermark_video_ai_max_frames: number;
  watermark_inpaint_prompt: string;
  google_oauth_client_id: string;
  google_oauth_redirect_uri: string;
  has_youtube_api_key: boolean;
  has_aliyun_access_key_secret: boolean;
  has_tencent_cos_secret_key: boolean;
  has_volc_cv_secret_access_key: boolean;
  has_google_oauth_client_secret: boolean;
  youtube_api_key_display: string | null;
  aliyun_access_key_secret_display: string | null;
  tencent_cos_secret_key_display: string | null;
  volc_cv_secret_access_key_display: string | null;
};

export type IntegrationTestResult = { ok: boolean; message: string };

export type IntegrationSettingsUpdatePayload = Partial<{
  youtube_api_key: string | null;
  active_storage_provider: string | null;
  aliyun_access_key_id: string | null;
  aliyun_access_key_secret: string | null;
  aliyun_role_arn: string | null;
  aliyun_region_id: string | null;
  aliyun_oss_bucket_name: string | null;
  aliyun_oss_endpoint: string | null;
  aliyun_custom_domain: string | null;
  tencent_cos_secret_id: string | null;
  tencent_cos_secret_key: string | null;
  tencent_cos_region: string | null;
  tencent_cos_bucket: string | null;
  tencent_custom_domain: string | null;
  volc_cv_access_key_id: string | null;
  volc_cv_secret_access_key: string | null;
  volc_cv_region: string | null;
  volc_cv_host: string | null;
  volc_cv_inpaint_req_key: string | null;
  watermark_video_ai_max_frames?: number | null;
  watermark_inpaint_prompt?: string | null;
  google_oauth_client_id: string | null;
  google_oauth_client_secret: string | null;
  google_oauth_redirect_uri: string | null;
}>;

export async function getIntegrationSettingsApi() {
  const res = await apiClient.get("/api/users/me/integration-settings");
  return res.data as IntegrationSettingsRead;
}

export async function updateIntegrationSettingsApi(payload: IntegrationSettingsUpdatePayload) {
  const res = await apiClient.put("/api/users/me/integration-settings", payload);
  return res.data as IntegrationSettingsRead;
}

export async function deleteIntegrationSettingsApi() {
  await apiClient.delete("/api/users/me/integration-settings");
}

export async function testYoutubeIntegrationApi() {
  const res = await apiClient.post("/api/users/me/integration-settings/test-youtube");
  return res.data as IntegrationTestResult;
}

export async function testStorageIntegrationApi() {
  const res = await apiClient.post("/api/users/me/integration-settings/test-storage");
  return res.data as IntegrationTestResult;
}

/** 校验自定义访问域名格式与网络可达性（不写入数据库） */
export async function validateStorageCustomDomainApi(payload: {
  platform: "aliyun" | "tencent";
  domain: string;
}) {
  const res = await apiClient.post("/api/users/me/integration-settings/validate-storage-custom-domain", payload);
  return res.data as IntegrationTestResult;
}
