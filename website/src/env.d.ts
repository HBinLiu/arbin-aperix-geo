/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PAYLOAD_API_URL?: string;
  readonly BACKEND_API_URL?: string;
  readonly PAYLOAD_SECRET?: string;
  /** 注册入口（CTA）；缺省 /auth/register */
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
