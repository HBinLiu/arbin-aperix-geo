import axios, { isAxiosError } from "axios";

import { clearStoredAvatarSeed } from "@/lib/avatar";
import { sanitizeReturnPath } from "@/lib/auth";
import { toast } from "@/lib/toast";

/** 默认请求超时（含 LLM 分析类接口，与后端 chat_completion 120s 对齐） */
export const API_TIMEOUT_MS = 120_000;

/** 主题步等待后台画像就绪 */
export const SETUP_TOPICS_TIMEOUT_MS = 180_000;

/** 初始提示词生成（LLM） */
export const GENERATE_PROMPTS_TIMEOUT_MS = 180_000;

declare module "axios" {
  interface AxiosRequestConfig {
    /** 为 true 时不弹出右下角错误 Toast（仍 reject，供调用方自行处理） */
    skipErrorToast?: boolean;
  }
}

/** 与 Vite 代理一致：请求发到当前 origin，由 dev server 转发到 FastAPI */
export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
  timeout: API_TIMEOUT_MS,
});

const TOKEN_KEY = "aperix_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
  clearStoredAvatarSeed();
}

api.interceptors.request.use((config) => {
  const t = getStoredToken();
  if (t) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

let authRedirecting = false;

function isPublicAuthRequest(url: string | undefined): boolean {
  if (!url) return false;
  return /\/auth\/(login|send-code|login-with-otp)(\/|$|\?)/.test(url);
}

function redirectToLogin(): void {
  if (authRedirecting || window.location.pathname.startsWith("/auth/")) return;
  authRedirecting = true;
  clearStoredToken();
  const next = sanitizeReturnPath(`${window.location.pathname}${window.location.search}`);
  window.location.replace(`/auth/login?next=${encodeURIComponent(next)}`);
}

function shouldToastApiError(error: unknown): boolean {
  if (!isAxiosError(error)) return true;
  if (error.code === "ERR_CANCELED") return false;
  if (error.config?.skipErrorToast) return false;
  const status = error.response?.status;
  if (status === 401 && !isPublicAuthRequest(error.config?.url)) return false;
  return true;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isAxiosError(error) && error.response?.status === 401 && !isPublicAuthRequest(error.config?.url)) {
      redirectToLogin();
    } else if (shouldToastApiError(error)) {
      toast.error(formatApiError(error));
    }
    return Promise.reject(error);
  },
);

/** 将 axios 错误转为用户可读中文 */
export function formatApiError(e: unknown, fallback = "请求失败"): string {
  if (isAxiosError(e)) {
    const status = e.response?.status;
    if (status === 403) {
      return "没有权限访问该资源。";
    }
    if (e.response) {
      const d = e.response.data as { detail?: unknown } | undefined;
      const detail = d?.detail;
      if (typeof detail === "object" && detail !== null && "message" in detail) {
        const message = (detail as { message?: unknown }).message;
        if (typeof message === "string" && message.trim()) return message;
      }
      // Prefer explicit server detail over the generic 402 fallback.
      if (typeof detail === "string" && detail.trim()) return detail;
      if (status === 402) {
        return "配额已用尽，请升级计划或购买配额包。";
      }
      if (Array.isArray(detail)) return JSON.stringify(detail);
      return `请求失败（HTTP ${status}）`;
    }
    return fallback;
  }
  if (e instanceof Error) return e.message;
  return fallback;
}

/** 手动弹出 API 错误 Toast（拦截器已覆盖大多数请求，仅在非 axios 场景使用） */
export function showApiError(e: unknown, fallback = "请求失败"): void {
  toast.error(formatApiError(e, fallback));
}
