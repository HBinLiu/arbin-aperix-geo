import { APERIX_CONTACT_QR } from "@shared/aperix";

const FRONTEND_IMAGES = "/assets/images/frontend";

/** 鉴权/Setup 背景图（固定 URL，开发/构建均由 shared/vite-plugin-shared-assets 提供） */
export const AUTH_LIGHT_BG = `${FRONTEND_IMAGES}/auth-light-bg.webp`;
export const AUTH_DARK_BG = `${FRONTEND_IMAGES}/auth-dark-bg.webp`;
export const SETUP_LIGHT_BG = `${FRONTEND_IMAGES}/setup-light.webp`;

/** 联系客服 / 联系我们 / 联系销售二维码 */
export const CONTACT_QR_IMAGE = APERIX_CONTACT_QR;

/** @deprecated 使用 CONTACT_QR_IMAGE */
export const CUSTOMER_IMAGE = CONTACT_QR_IMAGE;
