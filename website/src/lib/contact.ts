import { payloadApiBase } from "@/lib/payload";
import { resolveSiteCopyDeep } from "@/lib/site";

const CONTACT_TIMEOUT_MS = 30_000;

export type ContactBenefitIcon = "clock" | "messages" | "scan";

export type ContactBenefit = {
  icon: ContactBenefitIcon;
  title: string;
  description: string;
};

export type ContactFormCopy = {
  title: string;
  nameLabel: string;
  namePlaceholder: string;
  nameError: string;
  phoneLabel: string;
  phonePlaceholder: string;
  phoneError: string;
  emailLabel: string;
  emailPlaceholder: string;
  emailError: string;
  companyLabel: string;
  companyPlaceholder: string;
  companyError: string;
  messageLabel: string;
  messagePlaceholder: string;
  messageMaxLength: number;
  submitLabel: string;
  submittingLabel: string;
  submitError: string;
  footerNote: string;
  successTitle: string;
  successDescription: string;
};

export type ContactSubmission = {
  name: string;
  phone: string;
  email: string;
  company: string;
  message: string;
};

export type ContactSubmitResult =
  | { ok: true }
  | { ok: false; error: string };

export async function submitContactForm(
  data: ContactSubmission,
): Promise<ContactSubmitResult> {
  try {
    const res = await fetch(`${payloadApiBase()}/contact`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(CONTACT_TIMEOUT_MS),
    });

    const body = (await res.json().catch(() => null)) as { error?: string } | null;

    if (!res.ok) {
      return {
        ok: false,
        error: body?.error || "提交失败，请稍后再试。",
      };
    }

    return { ok: true };
  } catch {
    return { ok: false, error: "网络异常，请稍后再试。" };
  }
}

export const contactPage = resolveSiteCopyDeep({
  titleBefore: "获取",
  titleHighlight: "演示",
  description:
    "了解 {{siteName}} 如何帮助您的品牌在 AI 搜索中获得可见性和信任。也可咨询 GEO 时代官网定制与改造。",
  benefits: [
    {
      icon: "clock" as const,
      title: "20 分钟演示",
      description: "针对您需求的快速概览。",
    },
    {
      icon: "messages" as const,
      title: "免费品牌审计",
      description: "查看您当前的 AI 可见性评分。",
    },
    {
      icon: "scan" as const,
      title: "官网定制服务",
      description: "建设可被 AI 引用的品牌官网，了解服务详情。",
    },
  ] satisfies ContactBenefit[],
  qr: {
    title: "微信扫码联系",
    description: "添加顾问，快速沟通演示安排。",
  },
  form: {
    title: "填写您的需求",
    nameLabel: "姓名",
    namePlaceholder: "输入您的姓名",
    nameError: "请输入姓名",
    phoneLabel: "联系电话",
    phonePlaceholder: "13800000000",
    phoneError: "请输入有效的手机号",
    emailLabel: "工作邮箱",
    emailPlaceholder: "you@company.com",
    emailError: "请输入有效的邮箱地址",
    companyLabel: "公司名称",
    companyPlaceholder: "您的公司名称",
    companyError: "请输入公司名称",
    messageLabel: "您希望通过 GEO 实现什么目标？",
    messagePlaceholder: "例如：预约产品演示、咨询 GEO 官网定制、了解竞品可见性…",
    messageMaxLength: 300,
    submitLabel: "提交需求",
    submittingLabel: "正在提交...",
    submitError: "提交失败，请稍后再试。",
    footerNote: "我们将在 24 小时内回复。",
    successTitle: "提交成功",
    successDescription: "感谢您的留言，我们的团队将在 24 小时内与您联系。",
  } satisfies ContactFormCopy,
});
