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
  // YouTube 批量拉取（尤其 /api/youtube/analyze/batch 与 /channels/batch-update）可能耗时较长，
  // 需要避免被过短的 axios 超时提前中断（导致前端表现为“接口异常/监听通道关闭”等）。
  timeout: 120000,
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
      const isAuthRoute = url.includes("/api/auth/login") || url.includes("/api/auth/register") || url.includes("/api/auth/forgot-password") || url.includes("/api/auth/reset-password") || url.includes("/api/auth/send-email-code") || url.includes("/api/auth/captcha");
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

/**
 * 统一认证 fetch：用于 SSE/流式等需要原生 fetch 的场景，
 * 自动注入 Authorization header 并处理 401。
 */
export async function authFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const resp = await fetch(url, { ...init, headers });
  if (resp.status === 401 && typeof window !== "undefined") {
    localStorage.removeItem("access_token");
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
  return resp;
}

