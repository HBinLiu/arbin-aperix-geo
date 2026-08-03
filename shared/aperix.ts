/** Aperix 品牌 logo / favicon 公共资源路径（frontend / website 共用） */

/** 与 shared/assets/aperix/ 目录对应，经 /assets/aperix/* 提供 */
export const APERIX_ASSETS = "/assets/aperix";

export const APERIX_LOGO_SRC = {
  /** 浅色背景用的深色 logo */
  dark: `${APERIX_ASSETS}/logo_dark.webp`,
  /** 深色背景用的浅色 logo */
  light: `${APERIX_ASSETS}/logo_light.webp`,
} as const;

export const APERIX_FAVICON_ICO = `${APERIX_ASSETS}/favicon.ico`;
export const APERIX_FAVICON_PNG = `${APERIX_ASSETS}/favicon.png`;

/** 客服 / 联系我们 / 联系销售共用二维码 */
export const APERIX_CONTACT_QR = `${APERIX_ASSETS}/contact_us.png`;

export type AperixLogoVariant = keyof typeof APERIX_LOGO_SRC;
