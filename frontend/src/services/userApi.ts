import apiClient from "./apiClient";

export type UserSettings = {
  feishu_doc_url: string | null;
  ai_api_base_url: string | null;
  ai_models_json: string | null;
  ai_prompt_config_json: string | null;
  has_ai_api_key: boolean;
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
