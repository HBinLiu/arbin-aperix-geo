/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PAYLOAD_API_URL?: string;
  readonly BACKEND_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "*.webm" {
  const src: string;
  export default src;
}
