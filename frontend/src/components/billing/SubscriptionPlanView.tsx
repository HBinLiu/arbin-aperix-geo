import { useState } from "react";
import { Check } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TextBadge } from "@/components/ui/badge";
import {
  CURRENT_PLAN_ID,
  planCardTitle,
  planCycleSuffix,
  planDisplayPrice,
  SUBSCRIPTION_PLANS,
  type BillingCycle,
  type SubscriptionPlan,
} from "@/lib/billing/plans";
import { cn } from "@/lib/utils";

function BillingCycleToggle({
  value,
  onChange,
}: {
  value: BillingCycle;
  onChange: (cycle: BillingCycle) => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-3">
      <div className="border-border grid h-10 grid-cols-2 gap-1 rounded-lg border bg-background p-1">
        <button
          type="button"
          className={cn(
            "rounded-md px-4 text-sm font-medium transition-all",
            value === "monthly"
              ? "bg-muted-background text-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={() => onChange("monthly")}
        >
          每月
        </button>
        <button
          type="button"
          className={cn(
            "rounded-md px-4 text-sm font-medium transition-all",
            value === "yearly"
              ? "bg-muted-background text-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={() => onChange("yearly")}
        >
          按年
        </button>
      </div>
      <TextBadge variant="success" className="rounded-md px-2 py-0.5 text-xs font-medium">
        选择年付可立省 15%
      </TextBadge>
    </div>
  );
}

function PlanCard({
  plan,
  cycle,
  isCurrent,
}: {
  plan: SubscriptionPlan;
  cycle: BillingCycle;
  isCurrent: boolean;
}) {
  const price = planDisplayPrice(plan, cycle);
  const isCustom = plan.monthlyPrice === null;

  return (
    <article
      className={cn(
        "relative flex h-full flex-col rounded-xl border bg-muted-background p-5 shadow-xs",
        isCurrent ? "border-primary ring-1 ring-primary/20" : "border-border",
      )}
    >
      {isCurrent ? (
        <TextBadge
          variant="primary"
          className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-md px-2.5 py-0.5 text-xs font-semibold"
        >
          当前计划
        </TextBadge>
      ) : null}

      <div className="space-y-3">
        <h3 className="text-base font-semibold tracking-tight">{planCardTitle(plan, cycle)}</h3>
        <p className="text-muted-foreground min-h-[3.75rem] text-sm leading-relaxed">{plan.description}</p>
        <div className="flex items-end gap-1 pt-1">
          <span className="text-3xl font-semibold tracking-tight tabular-nums">{price}</span>
          {!isCustom ? (
            <span className="text-muted-foreground pb-1 text-sm">{planCycleSuffix(cycle)}</span>
          ) : null}
        </div>
      </div>

      <div className="mt-5">
        {plan.cta === "current" ? (
          <Button type="button" variant="outline" className="h-11 w-full" disabled>
            当前计划
          </Button>
        ) : plan.cta === "contact" ? (
          <Button type="button" className="h-11 w-full">
            联系销售
          </Button>
        ) : (
          <Button type="button" className="h-11 w-full">
            选择计划
          </Button>
        )}
      </div>

      <div className="border-border mt-5 border-t pt-5">
        <p className="text-sm font-semibold">计划限制</p>
        <ul className="mt-3 space-y-2.5">
          {plan.limits.map((limit) => (
            <li key={limit.label} className="flex items-start justify-between gap-3 text-sm">
              <span className="inline-flex min-w-0 items-center gap-2">
                <Check className="text-primary size-4 shrink-0" aria-hidden />
                <span className="text-foreground">{limit.label}</span>
              </span>
              <span className="text-muted-foreground shrink-0 tabular-nums">{limit.value}</span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}

/** 订阅计划 · 定价卡片 */
export function SubscriptionPlanView() {
  const [cycle, setCycle] = useState<BillingCycle>("monthly");

  return (
    <div className="relative flex w-full flex-col">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[80%]"
        style={{
          backgroundImage:
            "linear-gradient(to right, color-mix(in srgb, var(--muted-foreground) 16%, transparent) 1px, transparent 1px), linear-gradient(to bottom, color-mix(in srgb, var(--muted-foreground) 16%, transparent) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage:
            "linear-gradient(to right, transparent 0%, rgb(0 0 0 / 0.35) 14%, rgb(0 0 0) 28%, rgb(0 0 0) 72%, rgb(0 0 0 / 0.35) 86%, transparent 100%)",
          WebkitMaskImage:
            "linear-gradient(to right, transparent 0%, rgb(0 0 0 / 0.35) 14%, rgb(0 0 0) 28%, rgb(0 0 0) 72%, rgb(0 0 0 / 0.35) 86%, transparent 100%)",
        }}
      />

      <div className="relative flex flex-col items-center gap-8 px-4 py-10 sm:px-6 lg:py-12">
        <div className="relative w-full py-2 sm:py-4">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 -top-24 -bottom-24 sm:-top-28 sm:-bottom-28"
            style={{
              background:
                "radial-gradient(ellipse 72% 52% at 50% 50%, color-mix(in srgb, var(--primary) 14%, transparent) 0%, color-mix(in srgb, var(--primary) 7%, transparent) 26%, color-mix(in srgb, var(--primary) 2%, transparent) 46%, transparent 62%)",
              maskImage:
                "radial-gradient(ellipse 100% 100% at 50% 50%, black 0%, black 32%, rgb(0 0 0 / 0.35) 48%, transparent 66%)",
              WebkitMaskImage:
                "radial-gradient(ellipse 100% 100% at 50% 50%, black 0%, black 32%, rgb(0 0 0 / 0.35) 48%, transparent 66%)",
            }}
          />
          <header className="relative z-10 mx-auto max-w-2xl text-center">
            <TextBadge variant="primary" className="px-3 py-1 text-sm font-semibold">
              定价计划
            </TextBadge>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">选择你的计划</h2>
            <p className="text-muted-foreground mt-2 text-sm font-medium leading-relaxed sm:text-base">
              覆盖国内主流 AI 平台，实时监控分析品牌在 AI 中的竞争表现。
            </p>
          </header>
        </div>

        <div className="relative z-10">
          <BillingCycleToggle value={cycle} onChange={setCycle} />
        </div>

        <div className="relative z-10 grid w-full max-w-6xl gap-4 md:grid-cols-2 xl:grid-cols-4">
          {SUBSCRIPTION_PLANS.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              cycle={cycle}
              isCurrent={plan.id === CURRENT_PLAN_ID}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
