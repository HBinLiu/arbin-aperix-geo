import { getWebsiteUrl } from "./urls";

export type PreviewPathDoc = {
  slug?: string | null;
};

type PreviewPathBuilder = (doc: PreviewPathDoc) => string | null;

/** 各 collection 的官网预览路径（不含域名与鉴权参数） */
const previewPathByCollection: Record<string, PreviewPathBuilder> = {
  researches: (doc) => {
    const slug = typeof doc?.slug === "string" ? doc.slug.trim() : "";
    if (!slug) return null;
    return `/preview/research/${encodeURIComponent(slug)}/`;
  },
};

export function buildCollectionPreviewPath(
  collectionSlug: string | undefined,
  doc: PreviewPathDoc,
): string | null {
  if (!collectionSlug) return null;
  return previewPathByCollection[collectionSlug]?.(doc) ?? null;
}

/** 官网预览 URL（新标签页；需 PAYLOAD_SECRET + CMS 登录 token） */
export function buildPreviewUrl(
  pathname: string,
  token?: string | null,
): string | null {
  const path = pathname.trim();
  if (!path.startsWith("/")) return null;

  const payloadSecret = process.env.PAYLOAD_SECRET?.trim();
  if (!payloadSecret) return null;

  const params = new URLSearchParams({ payloadSecret });
  if (token) params.set("token", token);

  const base = getWebsiteUrl().replace(/\/$/, "");
  const normalizedPath = path.endsWith("/") ? path : `${path}/`;
  return `${base}${normalizedPath}?${params}`;
}
