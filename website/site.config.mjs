/**
 * @typedef {Object} SiteVerification
 * @property {string} [baidu] 百度站长 `baidu-site-verification`
 * @property {string} [qihoo360] 360 站长 `360-site-verification`
 * @property {string} [bytedance] 头条/抖音搜索 `bytedance-verification-code`
 * @property {string} [bing] Bing Webmaster `msvalidate.01`
 * @property {string} [google] Google Search Console `google-site-verification`
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
 * @property {string} [bytedancePushToken] 头条站长「自动收录」push.js? 后的 token；可由 PUBLIC_BYTEDANCE_PUSH_TOKEN 覆盖
 * @property {string} [indexNowKey] IndexNow API key；根路径需有 `{key}.txt` 文件（内容为 key 本身）
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
  /** 站长验证码；也可由 PUBLIC_*_SITE_VERIFICATION 环境变量覆盖 */
  siteVerification: {
    baidu: "codeva-gKYs7LQKFy",
    bytedance: "bYnnji8tNYRfDtWnJhM/",
    qihoo360: "c8daf2f7eaaf25291bf990f1ef2f7e22",
    bing: "6ECCC6ED13B693A9DFD72DB00F57756A",
    google: "vL6PMgcfFC0PUPVL1IvtsyB3hFVQ4lpageYtsSituUQ",
  },
  /** 头条搜索站长 → 数据提交 → 自动收录；空则不注入脚本 */
  bytedancePushToken:
    "1d3b4bb5953ca6e18e819105f6d6cc372f0d07542236f0ffeb20d5c8fc57a2fc3d72cd14f8a76432df3935ab77ec54f830517b3cb210f7fd334f50ccb772134a",
  /** IndexNow：对应 public/{key}.txt；提交 URL 时使用同一 key */
  indexNowKey: "b3df3abf83c59fef5e3e50c5e225e042",
};
