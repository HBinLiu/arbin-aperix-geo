import type { Subject } from "@/types";
import { websiteUrlFromInput } from "@/lib/domain";

/** 顶栏展示：域名类型显示主域名，品牌类型显示规范品牌名。 */
export function subjectDisplayLabel(subject: Subject): string {
  if (subject.type === "domain" && subject.domain) {
    return subject.domain;
  }
  if (subject.brand) return subject.brand;
  return "监测主体";
}

/** 用于 favicon 解析的网站 URL；无 URL 时返回 null（显示占位图标）。 */
export function subjectFaviconUrl(subject: Subject): string | null {
  const website = subject.website_url?.trim();
  if (website) return website;
  if (subject.type === "domain" && subject.domain?.trim()) {
    return websiteUrlFromInput(subject.domain.trim());
  }
  return null;
}

/** 编辑表单初始别名。 */
export function subjectEditAliases(subject: Subject): string[] {
  return subject.aliases.map((a) => a.trim()).filter(Boolean);
}

/** 品牌页「网站」完整 URL。 */
export function subjectWebsiteUrl(subject: Subject): string | null {
  const url = subject.website_url?.trim();
  return url || null;
}

const ACTIVE_SUBJECT_STORAGE_KEY = "active_subject";

export function getStoredActiveSubjectId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_SUBJECT_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredActiveSubjectId(id: string): void {
  try {
    localStorage.setItem(ACTIVE_SUBJECT_STORAGE_KEY, id);
  } catch {
    /* ignore */
  }
}

export function clearStoredActiveSubjectId(): void {
  try {
    localStorage.removeItem(ACTIVE_SUBJECT_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** 按 activeId 匹配；无效时回退到列表首项（API 已按 created_at 降序）。 */
export function resolveActiveSubject(subjects: Subject[], activeId?: string | null): Subject | null {
  if (subjects.length === 0) return null;
  if (activeId) {
    const found = subjects.find((s) => s.id === activeId);
    if (found) return found;
  }
  return subjects[0];
}
