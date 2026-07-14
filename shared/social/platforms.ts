/** 官网社交平台（与 SiteFooter 一致） */
export const SOCIAL_PLATFORM_OPTIONS = [
  { label: "微信", value: "wechat" },
  { label: "微博", value: "weibo" },
  { label: "抖音", value: "douyin" },
  { label: "小红书", value: "xiaohongshu" },
  { label: "哔哩哔哩", value: "bilibili" },
  { label: "知乎", value: "zhihu" },
] as const;

export type SocialPlatform = (typeof SOCIAL_PLATFORM_OPTIONS)[number]["value"];

export const SOCIAL_PLATFORM_VALUES: readonly SocialPlatform[] = SOCIAL_PLATFORM_OPTIONS.map(
  (option) => option.value,
);

export const SOCIAL_PLATFORM_LABELS: Record<SocialPlatform, string> = {
  wechat: "微信",
  weibo: "微博",
  douyin: "抖音",
  xiaohongshu: "小红书",
  bilibili: "哔哩哔哩",
  zhihu: "知乎",
};
