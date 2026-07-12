import { nodemailerAdapter } from "@payloadcms/email-nodemailer";

/** 与 backend/.env.example 中 SMTP_* 命名保持一致 */
function smtpHost(): string {
  return process.env.SMTP_HOST?.trim() ?? "";
}

function defaultFromAddress(): string {
  return process.env.SMTP_FROM?.trim() || process.env.SMTP_USER?.trim() || "cms@localhost";
}

function defaultFromName(): string {
  return process.env.SMTP_FROM_NAME?.trim() || "Aperix Web";
}

/** Payload 邮件：生产走 SMTP；本地未配置时用 Ethereal 测试账号（消除 no adapter WARN） */
export function createEmailAdapter() {
  const fromAddress = defaultFromAddress();
  const fromName = defaultFromName();

  if (!smtpHost()) {
    return nodemailerAdapter({
      defaultFromAddress: fromAddress,
      defaultFromName: fromName,
      skipVerify: true,
    });
  }

  const port = Number(process.env.SMTP_PORT || 587);
  const useTls = process.env.SMTP_USE_TLS !== "false";
  const user = process.env.SMTP_USER?.trim();

  return nodemailerAdapter({
    defaultFromAddress: fromAddress,
    defaultFromName: fromName,
    skipVerify: process.env.NODE_ENV !== "production",
    transportOptions: {
      host: smtpHost(),
      port,
      secure: port === 465,
      ...(useTls && port !== 465 ? { requireTLS: true } : {}),
      ...(user
        ? {
            auth: {
              user,
              pass: process.env.SMTP_PASSWORD?.trim() || process.env.SMTP_PASS?.trim() || "",
            },
          }
        : {}),
    },
  });
}
