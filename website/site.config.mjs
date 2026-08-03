/**
 * @typedef {Object} SiteVerification
 * @property {string} [baidu] 百度站长 `baidu-site-verification`
 * @property {string} [sogou] 搜狗站长 `sogou_site_verification`
 * @property {string} [qihoo360] 360 站长 `360-site-verification`
 * @property {string} [shenma] 神马搜索 `shenma-site-verification`
 * @property {string} [bytedance] 头条/抖音搜索 `bytedance-verification-code`
 */

/**
 * @typedef {Object} SiteConfig
 * @property {string} url
 * @property {string} name
 * @property {string} description
 * @property {string} keywords
 * @property {string} logo
 * @property {string} ogImage
 * @property {SiteVerification} [siteVerification]
 */

/** 官网站点配置唯一来源（astro.config / src 均从此读取；品牌名占位符 `{{siteName}}` 见 src/lib/site.ts） */
/** @type {SiteConfig} */
export const siteConfig = {
  url: "https://www.aperix.cn",
  name: "Aperix AI",
  description: "GEO 监测平台",
  keywords: "GEO,生成式引擎优化,AI可见性,AI搜索,品牌监测,Aperix,艾佩睿思",
  logo: "/assets/aperix/logo_dark.webp",
  ogImage: "/assets/images/website/og-default.webp",
  /** 国内站长验证码；也可由 PUBLIC_*_SITE_VERIFICATION 环境变量覆盖 */
  siteVerification: {
    baidu: "codeva-gKYs7LQKFy",
    sogou: "",
    qihoo360: "",
    shenma: "",
    bytedance: "",
  },
};
