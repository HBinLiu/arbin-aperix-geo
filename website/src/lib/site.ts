/** 官网全局站点配置（品牌名唯一来源） */
export type SiteConfig = {
  name: string;
  description: string;
};

export const siteConfig: SiteConfig = {
  name: "Aperix AI",
  description: "GEO 监测平台",
};

/** 文案占位符：lib/*.ts 中写 {{name}}，由 vite-plugin-site-config 在构建时替换 */
export const SITE_NAME_PLACEHOLDER = "{{name}}";
