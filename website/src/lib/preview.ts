import { timingSafeEqual } from "node:crypto";

function readPayloadSecret(): string {
  return (import.meta.env.PAYLOAD_SECRET ?? "").trim();
}

/** 校验 Payload Admin 生成的 payloadSecret 查询参数 */
export function isPayloadSecretValid(provided: string | null | undefined): boolean {
  const expected = readPayloadSecret();
  const actual = provided?.trim() ?? "";
  if (!expected || !actual) return false;

  const expectedBuf = Buffer.from(expected);
  const actualBuf = Buffer.from(actual);
  if (expectedBuf.length !== actualBuf.length) return false;

  return timingSafeEqual(expectedBuf, actualBuf);
}

export function isPreviewRequestAuthorized(
  payloadSecret: string | null | undefined,
  token: string | null | undefined,
): boolean {
  return isPayloadSecretValid(payloadSecret) && Boolean(token?.trim());
}
