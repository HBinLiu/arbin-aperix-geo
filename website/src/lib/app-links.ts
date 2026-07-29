import { APP_LINK_KEYS, isAppLinkKey, type AppLinkKey } from "@shared/app-links";

function envUrl(name: "PUBLIC_REGISTER_URL" | "PUBLIC_LOGIN_URL", fallback: string): string {
  const value = import.meta.env[name];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

/** 构建期解析后的注册 / 登录 URL（来自 PUBLIC_*，缺省为同域相对路径） */
export const appLinks = {
  register: envUrl("PUBLIC_REGISTER_URL", "/auth/login"),
  login: envUrl("PUBLIC_LOGIN_URL", "/auth/login"),
} as const;

/**
 * 将 CMS AppLinkKey（register / login）解析为最终 href。
 * 非键值（如 /contact/）原样返回；空值回落注册链接。
 */
export function resolveAppLink(value: string | null | undefined): string {
  const raw = value?.trim();
  if (!raw) return appLinks.register;
  if (isAppLinkKey(raw)) return appLinks[raw];
  return raw;
}

export { APP_LINK_KEYS, type AppLinkKey };
