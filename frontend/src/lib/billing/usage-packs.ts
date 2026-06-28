export function formatUsagePackPrice(priceCents: number): string {
  return `¥${(priceCents / 100).toLocaleString("zh-CN")}`;
}

export function formatUsagePackUnitPrice(unitPriceCents: number): string {
  return `¥${(unitPriceCents / 100).toFixed(2)}/次`;
}

export function formatUsagePackSubtitle(unitPriceCents: number): string {
  return formatUsagePackUnitPrice(unitPriceCents);
}
