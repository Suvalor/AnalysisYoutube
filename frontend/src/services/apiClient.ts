import axios from "axios";

/**
 * 统一后端根地址：所有请求路径均以 `/api/...` 开头。
 * 若环境变量写成 `https://host/api`，axios 会拼成 `https://host/api/api/...` 导致 404。
 */
function normalizeBackendBaseURL(raw: string | undefined): string {
  let base = (raw?.trim() || "http://localhost:8000").replace(/\/+$/, "");
  if (base.endsWith("/api")) {
    base = base.slice(0, -4).replace(/\/+$/, "");
  }
  return base || "http://localhost:8000";
}

const apiClient = axios.create({
  baseURL: normalizeBackendBaseURL(import.meta.env.VITE_API_BASE_URL),
  timeout: 10000,
});

apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

/** 受保护接口返回 401 时清除本地令牌并跳转登录（登录/注册接口的 401 不跳转） */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = String(error?.config?.url ?? "");
    if (status === 401 && typeof window !== "undefined") {
      const isAuthRoute = url.includes("/api/auth/login") || url.includes("/api/auth/register");
      if (!isAuthRoute) {
        localStorage.removeItem("access_token");
        if (!window.location.pathname.startsWith("/login")) {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

