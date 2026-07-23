/** Payload 服务根 URL（CORS） */
export function getPayloadServerUrl(): string {
  return (process.env.PAYLOAD_SERVER_URL || "http://localhost:3000").replace(/\/$/, "");
}

/** 官网根 URL（CORS） */
export function getWebsiteUrl(): string {
  return (process.env.PUBLIC_WEBSITE_URL || "http://localhost:4321").replace(/\/$/, "");
}
