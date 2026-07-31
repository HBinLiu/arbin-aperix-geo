/**
 * @typedef {Object} SiteConfig
 * @property {string} url
 * @property {string} name
 * @property {string} description
 * @property {string} logo
 * @property {string} ogImage
 */

/** 官网站点配置唯一来源（astro.config / src 均从此读取；品牌名占位符 `{{siteName}}` 见 src/lib/site.ts） */
/** @type {SiteConfig} */
export const siteConfig = {
  url: "https://www.aperix.cn",
  name: "Aperix AI",
  description: "GEO 监测平台",
  logo: "/assets/aperix/logo_dark.webp",
  ogImage: "/assets/images/website/og-default.webp",
};
