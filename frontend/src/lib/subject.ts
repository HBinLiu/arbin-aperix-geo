import type { Subject } from "@/types";

/** 顶栏展示：域名类型显示主域名，品牌类型显示规范品牌名。 */
export function subjectDisplayLabel(subject: Subject): string {
  if (subject.type === "domain" && subject.domain) {
    return subject.domain;
  }
  if (subject.brand) return subject.brand;
  return "监测主体";
}

export function subjectFaviconTarget(subject: Subject): string {
  if (subject.type === "domain" && subject.domain) {
    return subject.domain;
  }
  return subject.brand;
}

/** 品牌页「名称」：优先主域名，否则规范品牌名。 */
export function subjectPrimaryName(subject: Subject): string {
  return subjectDisplayLabel(subject);
}

/** 品牌页「别名」：aliases 首项，或品牌规范名（域名主体时）。 */
export function subjectAlias(subject: Subject): string | null {
  const first = subject.aliases.find((a) => a.trim());
  if (first) return first.trim();
  if (subject.type === "domain" && subject.brand?.trim()) {
    return subject.brand.trim();
  }
  return null;
}

/** 编辑表单初始别名：优先 aliases，域名主体可回退 brand。 */
export function subjectEditAliases(subject: Subject): string[] {
  const fromAliases = subject.aliases.map((a) => a.trim()).filter(Boolean);
  if (fromAliases.length > 0) return fromAliases;
  if (subject.type === "domain" && subject.brand?.trim()) {
    return [subject.brand.trim()];
  }
  return [];
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
