import type { User } from "@/types";

/** 登录后跳转路径：仅允许站内相对路径，避免开放重定向。 */
export function sanitizeReturnPath(raw: string | null): string {
  const fallback = "/";
  if (raw == null || typeof raw !== "string") return fallback;
  const t = raw.trim();
  if (!t.startsWith("/") || t.startsWith("//")) return fallback;
  if (t.includes(":")) return fallback;
  if (t.startsWith("/auth")) return fallback;
  return t || fallback;
}

export function userDisplayName(user: User): string {
  if (user.email) {
    const local = user.email.split("@")[0]?.trim();
    if (local) return local;
  }
  if (user.phone) {
    const tail = user.phone.replace(/\D/g, "").slice(-4);
    if (tail) return `用户${tail}`;
  }
  return "用户";
}

/** 用户菜单主标题：优先手机号 */
export function userPrimaryLabel(user: User): string {
  const phone = user.phone?.trim();
  if (phone) return phone;
  const email = user.email?.trim();
  if (email) return email;
  return "用户";
}

/** 用户菜单副标题：有手机号时展示邮箱 */
export function userSecondaryLabel(user: User): string | null {
  const phone = user.phone?.trim();
  const email = user.email?.trim();
  if (phone && email) return email;
  return null;
}

export function userAvatarInitial(user: User): string {
  return userDisplayName(user).slice(0, 1).toUpperCase();
}
