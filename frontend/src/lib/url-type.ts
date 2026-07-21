/** URL / page-type labels (aligned with web-page-classifier / rs-trafilatura). */
export const URL_TYPE_LABELS: Record<string, string> = {
  article: "文章",
  collection: "合集/类目",
  documentation: "文档",
  forum: "论坛/讨论",
  listing: "列表/索引",
  product: "商品",
  service: "服务页",
  other: "其他",
};

export function urlTypeLabel(urlType: string | null | undefined): string {
  const key = (urlType ?? "").trim().toLowerCase() || "other";
  return URL_TYPE_LABELS[key] ?? key;
}
