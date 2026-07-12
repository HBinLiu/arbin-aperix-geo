import type { Endpoint, PayloadRequest } from "payload";
import { headersWithCors } from "payload";

const PHONE_REG = /^1[3-9]\d{9}$/;
const EMAIL_REG = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type ContactBody = {
  name?: string;
  phone?: string;
  email?: string;
  company?: string;
  message?: string;
};

function corsHeaders(req: PayloadRequest): Headers {
  return headersWithCors({
    headers: new Headers(),
    req,
  });
}

function jsonResponse(req: PayloadRequest, body: unknown, status = 200): Response {
  return Response.json(body, {
    status,
    headers: corsHeaders(req),
  });
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function normalizePhoneCn(value: string): string | null {
  const digits = value.replace(/\D/g, "");
  const normalized =
    digits.length === 13 && digits.startsWith("86") ? digits.slice(2) : digits;
  if (!PHONE_REG.test(normalized)) return null;
  return normalized;
}

function contactEmailTo(): string {
  return (
    process.env.CONTACT_EMAIL_TO?.trim() ||
    process.env.SMTP_FROM?.trim() ||
    process.env.SMTP_USER?.trim() ||
    ""
  );
}

function siteName(): string {
  return process.env.CONTACT_SITE_NAME?.trim() || "Aperix";
}

async function handleContactPost(req: PayloadRequest): Promise<Response> {
  let body: ContactBody;
  try {
    if (!req.json) {
      return jsonResponse(req, { error: "请求格式无效" }, 400);
    }
    body = (await req.json()) as ContactBody;
  } catch {
    return jsonResponse(req, { error: "请求格式无效" }, 400);
  }

  const name = body.name?.trim() ?? "";
  const phoneRaw = body.phone?.trim() ?? "";
  const email = body.email?.trim() ?? "";
  const company = body.company?.trim() ?? "";
  const message = body.message?.trim() ?? "";

  if (!name) return jsonResponse(req, { error: "请输入姓名" }, 400);
  const phone = normalizePhoneCn(phoneRaw);
  if (!phone) return jsonResponse(req, { error: "请输入有效的 11 位手机号" }, 400);
  if (!email || !EMAIL_REG.test(email)) {
    return jsonResponse(req, { error: "请输入有效的邮箱地址" }, 400);
  }
  if (!company) return jsonResponse(req, { error: "公司名称为必填项" }, 400);

  const toEmail = contactEmailTo();
  if (!toEmail) {
    req.payload.logger.error(
      "Contact form: missing CONTACT_EMAIL_TO / SMTP_FROM / SMTP_USER",
    );
    return jsonResponse(req, { error: "邮件功能未配置，请稍后再试。" }, 503);
  }

  const brand = siteName();
  const subject = `【${brand}】预约演示：${name} - ${company}`;
  const text = [
    `姓名：${name}`,
    `联系电话：${phone}`,
    `工作邮箱：${email}`,
    `公司：${company}`,
    `GEO 目标：${message || "未填写"}`,
  ].join("\n");

  const html = `
    <h2>【${escapeHtml(brand)}】新的预约演示</h2>
    <p><strong>姓名：</strong> ${escapeHtml(name)}</p>
    <p><strong>联系电话：</strong> ${escapeHtml(phone)}</p>
    <p><strong>工作邮箱：</strong> ${escapeHtml(email)}</p>
    <p><strong>公司：</strong> ${escapeHtml(company)}</p>
    <p><strong>GEO 目标：</strong></p>
    <p>${message ? escapeHtml(message).replace(/\n/g, "<br />") : "未填写"}</p>
    <hr />
    <p style="color:#888;font-size:12px;">来自 ${escapeHtml(brand)} 官网「联系我们」表单，请及时回复。</p>
  `;

  try {
    await req.payload.sendEmail({
      to: toEmail,
      replyTo: email,
      subject,
      text,
      html,
    });
  } catch (error) {
    req.payload.logger.error({ err: error }, "Contact form send failed");
    return jsonResponse(req, { error: "发送失败，请稍后再试。" }, 500);
  }

  return jsonResponse(req, { success: true });
}

export const contactEndpoint: Endpoint = {
  path: "/contact",
  method: "post",
  handler: handleContactPost,
};

export const contactOptionsEndpoint: Endpoint = {
  path: "/contact",
  method: "options",
  handler: async (req) =>
    new Response(null, {
      status: 204,
      headers: corsHeaders(req),
    }),
};
