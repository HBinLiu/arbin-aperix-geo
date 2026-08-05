/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PAYLOAD_API_URL?: string;
  readonly BACKEND_API_URL?: string;
  readonly PAYLOAD_SECRET?: string;
  /** 注册/试用入口（CTA）；缺省 /auth/login（验证码登录即开通） */
  readonly PUBLIC_REGISTER_URL?: string;
  /** 登录入口（CTA）；缺省 /auth/login */
  readonly PUBLIC_LOGIN_URL?: string;
  /** 百度站长验证码 */
  readonly PUBLIC_BAIDU_SITE_VERIFICATION?: string;
  /** 360 站长验证码 */
  readonly PUBLIC_360_SITE_VERIFICATION?: string;
  /** 头条/抖音搜索验证码 */
  readonly PUBLIC_BYTEDANCE_SITE_VERIFICATION?: string;
  /** Bing Webmaster 验证码 */
  readonly PUBLIC_BING_SITE_VERIFICATION?: string;
  /** Google Search Console 验证码 */
  readonly PUBLIC_GOOGLE_SITE_VERIFICATION?: string;
  /** 头条站长「自动收录」push.js token（查询串或完整 URL） */
  readonly PUBLIC_BYTEDANCE_PUSH_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "*.webm" {
  const src: string;
  export default src;
}

declare module "*.mp4" {
  const src: string;
  export default src;
}
