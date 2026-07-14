/** 官网 / CMS 共用的应用入口链接键（真实 URL 由 website 环境变量解析） */
export const APP_LINK_KEYS = {
  register: "register",
  login: "login",
} as const;

export type AppLinkKey = (typeof APP_LINK_KEYS)[keyof typeof APP_LINK_KEYS];

/** Payload select options */
export const APP_LINK_OPTIONS: Array<{ label: string; value: AppLinkKey }> = [
  { label: "注册链接", value: APP_LINK_KEYS.register },
  { label: "登录链接", value: APP_LINK_KEYS.login },
];

export function isAppLinkKey(value: string): value is AppLinkKey {
  return value === APP_LINK_KEYS.register || value === APP_LINK_KEYS.login;
}
