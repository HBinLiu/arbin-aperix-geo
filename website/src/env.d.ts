/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PAYLOAD_API_URL?: string;
  readonly BACKEND_API_URL?: string;
  readonly PAYLOAD_SECRET?: string;
  /** 注册/试用入口（CTA）；缺省 /auth/login（验证码登录即开通） */
  readonly PUBLIC_REGISTER_URL?: string;
  /** 登录入口（CTA）；缺省 /auth/login */
  readonly PUBLIC_LOGIN_URL?: string;
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
