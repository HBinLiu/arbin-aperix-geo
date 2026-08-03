import { siteConfig } from "@site";

export type SiteVerificationMeta = {
  name: string;
  content: string;
};

type VerificationKey = "baidu" | "sogou" | "qihoo360" | "shenma" | "bytedance";

const VERIFICATION_META: Record<
  VerificationKey,
  { name: string; env: keyof ImportMetaEnv }
> = {
  baidu: { name: "baidu-site-verification", env: "PUBLIC_BAIDU_SITE_VERIFICATION" },
  sogou: { name: "sogou_site_verification", env: "PUBLIC_SOGOU_SITE_VERIFICATION" },
  qihoo360: { name: "360-site-verification", env: "PUBLIC_360_SITE_VERIFICATION" },
  shenma: { name: "shenma-site-verification", env: "PUBLIC_SHENMA_SITE_VERIFICATION" },
  bytedance: {
    name: "bytedance-verification-code",
    env: "PUBLIC_BYTEDANCE_SITE_VERIFICATION",
  },
};

function envOrConfig(key: VerificationKey): string {
  const fromEnv = import.meta.env[VERIFICATION_META[key].env];
  if (typeof fromEnv === "string" && fromEnv.trim()) return fromEnv.trim();
  const fromConfig = siteConfig.siteVerification?.[key];
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
