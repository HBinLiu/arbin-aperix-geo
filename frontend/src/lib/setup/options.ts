/** 新增品牌/域名设置：地区 / 语言选项（展示用旗帜 emoji + 参考图式下拉文案） */

export const SETUP_REGIONS: { value: string; label: string; flag: string }[] = [
  { value: "CN", label: "CN (中国大陆)", flag: "🇨🇳" },
  { value: "HK", label: "HK (Hong Kong, China)", flag: "🇭🇰" },
  { value: "TW", label: "TW (Taiwan, China)", flag: "🇹🇼" },
  //{ value: "GLOBAL", label: "全球 / 不限", flag: "🌐" },
];

export const SETUP_LANGUAGES: { value: string; label: string; flag: string }[] = [
  { value: "zh-CN", label: "简体中文", flag: "🇨🇳" },
  { value: "zh-HK", label: "繁體中文（中国香港）", flag: "🇭🇰" },
  { value: "zh-TW", label: "繁體中文（中国台湾）", flag: "🇹🇼" },
  //{ value: "en", label: "English", flag: "🇺🇸" },
];

export function regionDisplay(value: string): string {
  return SETUP_REGIONS.find((r) => r.value === value)?.label ?? value;
}

/** 从 monitoring_scope JSON 读取地区 code（如 CN）。 */
export function regionFromMonitoringScope(
  scope: { region?: string },
): string {
  const value = scope?.region?.trim();
  return value || "CN";
}

export function languageFromMonitoringScope(
  scope: { language?: string },
): string {
  const value = scope?.language?.trim();
  return value || "zh-CN";
}

export function languageDisplay(value: string): string {
  return SETUP_LANGUAGES.find((l) => l.value === value)?.label ?? value;
}
