export type CmsMediaRef = {
  url?: string | null;
  alt?: string | null;
  width?: number | null;
  height?: number | null;
};

function cmsAssetUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (import.meta.env.DEV) {
    return `http://127.0.0.1:3000${normalized}`;
  }
  const site = import.meta.env.SITE?.replace(/\/$/, "");
  return site ? `${site}${normalized}` : normalized;
}

export function resolveNewsMediaUrl(
  media: CmsMediaRef | string | null | undefined,
  fallback = "",
): string {
  if (!media) return fallback;
  if (typeof media === "string") {
    return media.startsWith("http") ? media : cmsAssetUrl(media);
  }
  const url = media.url?.trim();
  if (!url) return fallback;
  return url.startsWith("http") ? url : cmsAssetUrl(url);
}

export function resolveNewsMediaAlt(
  media: CmsMediaRef | string | null | undefined,
  override?: string | null,
  fallback = "",
): string {
  const trimmed = override?.trim();
  if (trimmed) return trimmed;
  if (media && typeof media === "object") {
    const alt = media.alt?.trim();
    if (alt) return alt;
  }
  return fallback;
}
