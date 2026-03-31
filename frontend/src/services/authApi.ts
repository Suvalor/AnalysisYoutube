import apiClient from "./apiClient";

export type AuthFormValues = {
  email: string;
  password: string;
};

export async function registerApi(data: AuthFormValues) {
  const res = await apiClient.post("/api/auth/register", data);
  return res.data;
}

export async function loginApi(data: AuthFormValues) {
  const res = await apiClient.post("/api/auth/login", data);
  return res.data as { access_token: string; token_type: string };
}

