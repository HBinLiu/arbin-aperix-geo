import { DASHBOARD_APP_BASE } from "@/lib/dashboard";

export const DIAGNOSIS_BASE_PATH = `${DASHBOARD_APP_BASE}/diagnosis`;

const DIAGNOSIS_CONTENT_DETAIL_PREFIX = `${DIAGNOSIS_BASE_PATH}/`;

export function diagnosisContentDetailPath(promptId: string): string {
  return `${DIAGNOSIS_CONTENT_DETAIL_PREFIX}${encodeURIComponent(promptId)}`;
}

export function diagnosisContentPromptIdFromPathname(pathname: string): string | null {
  const normalized = pathname.replace(/\/+$/, "");
  if (normalized === DIAGNOSIS_BASE_PATH) {
    return null;
  }
  if (!normalized.startsWith(DIAGNOSIS_CONTENT_DETAIL_PREFIX)) {
    return null;
  }
  const encoded = normalized.slice(DIAGNOSIS_CONTENT_DETAIL_PREFIX.length).split("/")[0] ?? "";
  if (!encoded) {
    return null;
  }
  try {
    return decodeURIComponent(encoded).trim();
  } catch {
    return encoded.trim();
  }
}
