import { siteConfig } from "@site";

export type SiteVerificationMeta = {
  name: string;
  content: string;
};

type VerificationKey = "baidu" | "qihoo360" | "bytedance" | "bing";

const VERIFICATION_META: Record<
  VerificationKey,
  { name: string; env: keyof ImportMetaEnv }
> = {
  baidu: { name: "baidu-site-verification", env: "PUBLIC_BAIDU_SITE_VERIFICATION" },
  qihoo360: { name: "360-site-verification", env: "PUBLIC_360_SITE_VERIFICATION" },
  bytedance: {
    name: "bytedance-verification-code",
    env: "PUBLIC_BYTEDANCE_SITE_VERIFICATION",
  },
  bing: { name: "msvalidate.01", env: "PUBLIC_BING_SITE_VERIFICATION" },
};

/** 头条搜索站长 · 自动收录 push.js */
const BYTEDANCE_PUSH_JS = "https://lf1-cdn-tos.bytegoofy.com/goofy/ttzz/push.js";

function envOrConfig(key: VerificationKey): string {
  const fromEnv = import.meta.env[VERIFICATION_META[key].env];
  if (typeof fromEnv === "string" && fromEnv.trim()) return fromEnv.trim();
  const fromConfig = siteConfig.siteVerification?.[key];
  return typeof fromConfig === "string" ? fromConfig.trim() : "";
}

function bytedancePushToken(): string {
  const fromEnv = import.meta.env.PUBLIC_BYTEDANCE_PUSH_TOKEN;
  if (typeof fromEnv === "string" && fromEnv.trim()) return fromEnv.trim();
  const fromConfig = siteConfig.bytedancePushToken;
  return typeof fromConfig === "string" ? fromConfig.trim() : "";
}

/** 已配置的国内站长验证 meta（空值不输出） */
export function getSiteVerificationMetas(): SiteVerificationMeta[] {
  return (Object.keys(VERIFICATION_META) as VerificationKey[])
    .map((key) => {
      const content = envOrConfig(key);
      if (!content) return null;
      return { name: VERIFICATION_META[key].name, content };
    })
    .filter((item): item is SiteVerificationMeta => item !== null);
}

/**
 * 头条/抖音站长「自动收录」脚本 src；未配置 token 时返回 null。
 * token 来自站长后台 push.js? 后的查询串，也可直接填完整 https URL。
 */
export function getBytedanceAutoIncludeSrc(): string | null {
  const token = bytedancePushToken();
  if (!token) return null;
  if (/^https?:\/\//i.test(token)) return token;
  return `${BYTEDANCE_PUSH_JS}?${token}`;
}