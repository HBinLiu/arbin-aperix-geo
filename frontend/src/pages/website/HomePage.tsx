import { Link } from "react-router-dom";

import { getStoredToken } from "@/api/client";
import { Button } from "@/components/ui/button";

import "./marketing.css";

/** 官网进入控制台鉴权页时在新标签打开，保留当前营销页。 */
const AUTH_LINK_PROPS = { target: "_blank" as const, rel: "noopener noreferrer" };

/**
 * 对外官网初版（信息架构参考同类 GEO/品牌监测产品落地页：强 Hero、三步闭环、痛点与 FAQ、底部转化条）。
 */
export function HomePage() {
  const loginEntryPath = getStoredToken() ? "/app" : "/auth/login";

  return (
    <div className="bg-background flex min-h-svh flex-col">
      {/* 顶栏 */}
      <header className="border-border/40 bg-background/80 supports-backdrop-filter:bg-background/70 sticky top-0 z-50 border-b backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:h-16 sm:px-6">
          <Link
            to="/"
            className="flex shrink-0 items-center gap-2.5 rounded-md outline-hidden focus-visible:ring-2 focus-visible:ring-ring"
          >
            <img
              src="/logo.png"
              alt="Aperix AI"
              width={40}
              height={40}
              className="size-9 shrink-0 object-contain sm:size-10"
              decoding="async"
            />
            <span className="text-foreground text-lg font-semibold tracking-tight">
              Aperix <span className="text-primary">GEO</span>
            </span>
          </Link>
          <nav className="hidden items-center gap-8 text-sm font-medium text-foreground/80 md:flex">
            <a href="#capabilities" className="transition-colors hover:text-foreground">
              能力
            </a>
            <a href="#workflow" className="transition-colors hover:text-foreground">
              工作方式
            </a>
            <a href="#faq" className="transition-colors hover:text-foreground">
              常见问题
            </a>
          </nav>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <Button
              variant="ghost"
              size="sm"
              className="text-foreground/80 hover:bg-slate-100/90 hover:text-foreground dark:hover:bg-foreground/10"
              asChild
            >
              <Link to={loginEntryPath} {...AUTH_LINK_PROPS}>登录</Link>
            </Button>
            <Button size="sm" className="sm:h-9" asChild>
              <Link to="/auth/register" {...AUTH_LINK_PROPS}>开始免费试用</Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="flex flex-1 flex-col">
        {/* Hero — 深色条带 */}
        <section className="marketing-hero relative overflow-hidden">
          <div
            className="marketing-hero-glow pointer-events-none absolute inset-0 opacity-[0.4]"
            aria-hidden
          />
          <div className="relative mx-auto max-w-6xl px-4 py-20 sm:px-6 sm:py-28">
            <p className="marketing-muted mb-4 text-sm font-medium tracking-wide">
              品牌采样 · 解析 · 聚合 — 面向生成式对话与公开文本
            </p>
            <h1 className="max-w-4xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl sm:leading-[1.08] lg:text-6xl">
              你的品牌，在 AI 与公开对话里
              <span className="marketing-subtle mt-2 block">被怎样描述、与谁同框？</span>
            </h1>
            <p className="marketing-muted mt-8 max-w-2xl text-lg leading-relaxed sm:text-xl">
              Aperix AI 帮助团队按主体与竞品配置采样任务，统一提示词与证据链，把「被提及、被引用、情感与位次」沉淀为可复盘的数据——而不只是一次性截图。
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:items-center">
              <Button
                size="lg"
                className="marketing-cta-btn h-12 border-0 px-8 text-base font-semibold shadow-lg transition-opacity hover:opacity-90"
                asChild
              >
                <Link to="/auth/register" {...AUTH_LINK_PROPS}>免费注册</Link>
              </Button>
            </div>
            <ul className="marketing-subtle mt-8 flex flex-wrap gap-x-8 gap-y-2 text-sm">
              <li className="flex items-center gap-2">
                <span className="marketing-bullet size-1.5 shrink-0 rounded-full" aria-hidden />
                邮箱注册 + 密码；手机号短信验证即可开通
              </li>
              <li className="flex items-center gap-2">
                <span className="marketing-bullet size-1.5 shrink-0 rounded-full" aria-hidden />
                控制台与官网可同域部署
              </li>
            </ul>
          </div>
        </section>

        {/* 社会证明条 — 无虚构客户名，强调适用场景 */}
        <section className="border-border bg-background/40 border-y py-10">
          <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
            <p className="text-muted-foreground text-sm font-medium uppercase tracking-wider">适用团队</p>
            <p className="text-foreground mt-2 text-lg font-medium sm:text-xl">
              品牌与市场、增长与舆情、产品研究 — 需要<strong className="font-semibold">可重复采样与可追溯证据</strong>时
            </p>
          </div>
        </section>

        {/* 三步闭环 */}
        <section id="workflow" className="scroll-mt-20 py-20 sm:py-24">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className="text-foreground text-center text-3xl font-semibold tracking-tight sm:text-4xl">
              看见提及 → 读懂结构 → 推进迭代
            </h2>
            <p className="text-muted-foreground mx-auto mt-4 max-w-2xl text-center text-base leading-relaxed">
              与「只看一次回答」不同，Aperix AI 强调任务化采样与落库，便于对比时间窗口与提示词版本。
            </p>
            <div className="mt-14 grid gap-8 md:grid-cols-3">
              {[
                {
                  step: "01",
                  title: "监测 · 采样",
                  desc: "为主体与竞品配置主题、提示词与采样任务；对接可配置的国产/兼容 OpenAI 的模型端点。",
                  accent: "from-primary/25 to-transparent",
                },
                {
                  step: "02",
                  title: "理解 · 解析",
                  desc: "对原始回答做 v0 级解析：提及、URL、粗情感与简单位次等，为后续指标升级预留字段。",
                  accent: "from-muted-foreground/25 to-transparent",
                },
                {
                  step: "03",
                  title: "行动 · 聚合",
                  desc: "按任务与主体聚合只读视图，证据预览与全文可查，支撑内部分享与复盘会议。",
                  accent: "from-primary/30 to-transparent",
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className="border-border bg-background group relative overflow-hidden rounded-2xl border p-8 shadow-xs transition-shadow hover:shadow-md"
                >
                  <div
                    className={`pointer-events-none absolute -right-8 -top-8 size-40 rounded-full bg-linear-to-br ${item.accent}`}
                    aria-hidden
                  />
                  <span className="text-primary font-mono text-sm font-semibold">{item.step}</span>
                  <h3 className="text-foreground mt-3 text-xl font-semibold">{item.title}</h3>
                  <p className="text-muted-foreground mt-3 text-sm leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 痛点 + 方案 */}
        <section id="capabilities" className="scroll-mt-20 bg-background/30 border-y py-20 sm:py-24">
          <div className="mx-auto max-w-6xl space-y-16 px-4 sm:px-6">
            {[
              {
                pain: "手动问几次大模型，无法回答「这周和上周比，竞品多出现了几次」。",
                sol: "用采样任务把提示词、模型与时间窗口固定下来，结果落库，便于对比与导出思路。",
              },
              {
                pain: "截图散落在聊天记录里，复盘时找不到当时的完整原文与请求参数。",
                sol: "每条响应保留证据链与预览，支持按主体、主题、任务筛选，减少「当时到底是怎么问的」争议。",
              },
            ].map((block, i) => (
              <div
                key={i}
                className="grid items-start gap-8 lg:grid-cols-2 lg:gap-16"
              >
                <div>
                  <p className="text-error/90 text-sm font-semibold uppercase tracking-wide">常见痛点</p>
                  <p className="text-foreground mt-3 text-xl font-medium leading-snug sm:text-2xl">{block.pain}</p>
                </div>
                <div className="border-border bg-background rounded-2xl border p-8 shadow-xs lg:mt-8">
                  <p className="text-primary text-sm font-semibold uppercase tracking-wide">Aperix AI</p>
                  <p className="text-muted-foreground mt-3 leading-relaxed">{block.sol}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 数字条 — 真实能力向，不虚构客户规模 */}
        <section className="py-16 sm:py-20">
          <div className="mx-auto grid max-w-6xl gap-6 px-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
            {[
              { k: "多租户", v: "工作区隔离", d: "注册即租户，数据按租户边界管理。" },
              { k: "模型", v: "Env 可配", d: "兼容 OpenAI 协议的端点与模型名。" },
              { k: "任务", v: "异步队列", d: "批量采样由 Worker 执行，状态可轮询。" },
              { k: "证据", v: "可追溯", d: "响应与解析结果落库，便于审计。" },
            ].map((s) => (
              <div key={s.k} className="border-border rounded-xl border bg-background p-6 text-center shadow-xs">
                <p className="text-muted-foreground text-xs font-medium uppercase tracking-wider">{s.k}</p>
                <p className="text-foreground mt-2 text-2xl font-semibold">{s.v}</p>
                <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{s.d}</p>
              </div>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="scroll-mt-20 border-t py-20 sm:py-24">
          <div className="mx-auto max-w-3xl px-4 sm:px-6">
            <h2 className="text-foreground text-center text-3xl font-semibold tracking-tight">常见问题</h2>
            <div className="mt-10 space-y-3">
              {[
                {
                  q: "Aperix AI 和「自己问 ChatGPT」有什么区别？",
                  a: "把提问方式固化为可复用的采样任务，并把回答与解析结果结构化落库，支持多主体、竞品与时间维度的对比，而不是零散对话。",
                },
                {
                  q: "邮箱和手机号注册流程有什么不同？",
                  a: "邮箱需先完成注册（邮箱验证码 + 登录密码），之后用邮箱与密码登录。手机号在登录页使用短信验证码，若号码尚未开通，验证通过后会自动创建工作区。",
                },
                {
                  q: "当前解析能力到什么程度？",
                  a: "内置 v0 级解析（提及、链接、粗情感等）。指标口径与更细算法可在后续版本与文档中持续迭代。",
                },
                {
                  q: "数据存在哪里？",
                  a: "默认使用您自托管的 PostgreSQL 与 Redis；控制台通过 HTTP API 访问后端，便于与内网策略对齐。",
                },
              ].map((item) => (
                <details
                  key={item.q}
                  className="border-border group bg-background open:shadow-md rounded-xl border px-5 py-4 transition-shadow"
                >
                  <summary className="text-foreground cursor-pointer list-none text-left text-base font-medium [&::-webkit-details-marker]:hidden">
                    <span className="flex items-center justify-between gap-4">
                      {item.q}
                      <span className="text-muted-foreground group-open:rotate-180 text-xl transition-transform">▾</span>
                    </span>
                  </summary>
                  <p className="text-muted-foreground mt-4 border-border border-t pt-4 text-sm leading-relaxed">{item.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* 底部 CTA */}
        <section className="marketing-cta py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">准备好把工作流搬进控制台了吗？</h2>
            <p className="marketing-muted mx-auto mt-4 max-w-xl text-base leading-relaxed">
              从注册一个工作区开始，配置主体、竞品与主题，再发起你的第一条采样任务。
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-4">
              <Button
                size="lg"
                className="marketing-cta-btn h-12 border-0 px-8 font-semibold transition-opacity hover:opacity-90"
                asChild
              >
                <Link to="/auth/register" {...AUTH_LINK_PROPS}>开始免费试用</Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="marketing-outline-btn h-12 px-8"
                asChild
              >
                <Link to="/auth/register" {...AUTH_LINK_PROPS}>开始免费试用</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-border text-muted-foreground border-t py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 text-center text-sm sm:flex-row sm:px-6 sm:text-left">
          <p>© {new Date().getFullYear()} Aperix AI</p>
          <div className="flex flex-wrap justify-center gap-6">
            <Link
              to={loginEntryPath}
              className="hover:text-foreground underline-offset-4 hover:underline"
              {...AUTH_LINK_PROPS}
            >
              登录
            </Link>
            <Link
              to="/auth/register"
              className="hover:text-foreground underline-offset-4 hover:underline"
              {...AUTH_LINK_PROPS}
            >
              注册
            </Link>
            <Link to="/app" className="hover:text-foreground underline-offset-4 hover:underline">
              控制台
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
