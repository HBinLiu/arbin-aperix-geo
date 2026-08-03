import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Boxes,
  Building2,
  Check,
  CircleHelp,
} from "lucide-react";

import { createSubscriptionOrder } from "@/api/billing";
import { fetchSamplingPlatforms } from "@/api/brand";
import { formatApiError } from "@/api/client";
import { ActionTooltip } from "@/components/common/ActionTooltip";
import { PlanChangeConfirmDialog } from "@/components/billing/PlanChangeConfirmDialog";
import { PayOrderDialog } from "@/components/billing/PayOrderDialog";
import { ContactQrDialog } from "@/components/common/ContactQrDialog";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Button } from "@/components/ui/button";
import { TextBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { usePlanCatalog } from "@/hooks/usePlanCatalog";
import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import { formatBillingDate } from "@/lib/billing/format";
import {
  PLAN_LIMIT_ICONS,
  isMatchingSubscriptionPlan,
  planCardLimits,
  planChangeConfirmCopy,
  planChangePayDescription,
  planDisplayPrice,
  planComparisonRows,
  planSelectLabel,
  resolvePlanChangeKind,
  resolvePlanCta,
  type BillingCycle,
  type PlanCatalogItem,
  type PlanChangeConfirmCopy,
  type PlanChangeKind,
} from "@/lib/billing/plans";
import { isSubscriptionActive } from "@/lib/billing/subscription";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { toast } from "@/lib/toast";

function PlanFeatureLabel({ limitKey, label, description }: { limitKey: string; label: string; description: string }) {
  const Icon = PLAN_LIMIT_ICONS[limitKey] ?? Building2;

  return (
    <span className="inline-flex min-w-0 items-center gap-2">
      <span
        className="bg-primary/10 text-primary flex size-7 shrink-0 items-center justify-center rounded-full"
        aria-hidden
      >
        <Icon className="size-3.5" />
      </span>
      <span className="truncate">{label}</span>
      {description ? (
        <ActionTooltip label={description} className="whitespace-nowrap">
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            aria-label={`了解${label}`}
          >
            <CircleHelp className="size-4" aria-hidden />
          </button>
        </ActionTooltip>
      ) : null}
    </span>
  );
}

function BillingCycleToggle({
  cycles,
  value,
  onChange,
}: {
  cycles: { id: BillingCycle; label: string; badge?: string | null }[];
  value: BillingCycle;
  onChange: (cycle: BillingCycle) => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-center">
      <div className="border-border inline-flex min-h-10 items-center gap-1 rounded-full border bg-background p-1">
        {cycles.map((cycle) => (
          <button
            key={cycle.id}
            type="button"
            className={cn(
              "inline-flex w-auto shrink-0 items-center justify-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
              value === cycle.id
                ? "bg-muted-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
            onClick={() => onChange(cycle.id)}
          >
            {cycle.label}
            {cycle.badge ? (
              <TextBadge variant="success" className="rounded-full px-1.5 py-0 text-[10px] font-medium leading-4">
                {cycle.badge}
              </TextBadge>
            ) : null}
          </button>
        ))}
      </div>
    </div>
  );
}

const PLAN_LIMIT_SKELETON_ROWS = 6;
const PLATFORM_LOGO_SKELETON_COUNT = 6;

function PlanCardSkeleton() {
  return (
    <article
      aria-hidden
      className="flex h-full min-h-[430px] w-full flex-col rounded-3xl border border-border bg-muted-background p-6 shadow-sm"
    >
      <div className="flex min-h-0 flex-1 flex-col">
        <header className="shrink-0 space-y-2">
          <Skeleton className="h-7 w-24" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
          </div>
        </header>

        <section className="mt-2 shrink-0">
          <Skeleton className="h-10 w-28" />
        </section>

        <section className="mt-5 shrink-0">
          <Skeleton className="h-11 w-full rounded-xl" />
        </section>

        <section className="border-border mt-5 flex min-h-0 flex-1 flex-col border-t pt-5">
          <Skeleton className="h-4 w-16" />
          <ul className="mt-3 space-y-2.5">
            {Array.from({ length: PLAN_LIMIT_SKELETON_ROWS }, (_, index) => (
              <li key={index} className="flex items-center justify-between gap-3">
                <span className="inline-flex min-w-0 flex-1 items-center gap-2">
                  <Skeleton className="size-6 shrink-0 rounded-full" />
                  <Skeleton className="h-4 w-20" />
                </span>
                <Skeleton className="h-4 w-10 shrink-0" />
              </li>
            ))}
          </ul>
        </section>
      </div>
    </article>
  );
}

function PlanCard({
  plan,
  cycle,
  cta,
  onSelect,
  onContact,
  selecting,
  highlightAsBound,
  selectLabel = "立即订阅",
}: {
  plan: PlanCatalogItem;
  cycle: BillingCycle;
  cta: "current" | "select" | "contact";
  onSelect?: (plan: PlanCatalogItem, cycle: BillingCycle) => void;
  onContact?: () => void;
  selecting?: boolean;
  /** 仍为租户绑定计划（含已到期，用于高亮与角标）。 */
  highlightAsBound?: boolean;
  selectLabel?: string;
}) {
  const price = planDisplayPrice(plan, cycle);
  const isCustom = price === null;
  const isCurrent = cta === "current";
  const showBoundBadge = isCurrent || Boolean(highlightAsBound);

  return (
    <article
      className={cn(
        "group relative flex h-full min-h-[430px] w-full flex-col rounded-3xl border bg-muted-background p-6 shadow-sm transition-[transform,box-shadow] duration-500 ease-out hover:-translate-y-1.5 hover:shadow-xl hover:shadow-primary/10",
        showBoundBadge
          ? "border-primary shadow-[0_0_0_2px_var(--primary)] hover:border-primary"
          : "border-border hover:border-primary/60",
      )}
    >
      {showBoundBadge ? (
        <TextBadge
          variant="primary"
          className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 bg-primary px-3 py-1 text-xs font-bold text-primary-foreground"
        >
          {isCurrent ? "当前订阅" : "已到期"}
        </TextBadge>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col">
        {/* 标题区 */}
        <header className="shrink-0 space-y-2">
          <h3 className="min-h-6 text-2xl font-semibold tracking-tight">{plan.name}</h3>
          <p className="text-muted-foreground min-h-[4.5rem] text-sm font-medium leading-relaxed">{plan.description}</p>
        </header>

        {/* 价格区 */}
        <section className="mt-2 shrink-0" aria-label="价格">
          <div className="inline-flex items-baseline gap-0.5">
            {isCustom ? (
              <span className="text-4xl font-semibold tracking-tight">自定义</span>
            ) : (
              <>
                <span className="-translate-y-0.5 text-lg font-semibold">¥</span>
                <span className="text-4xl font-semibold tracking-tight tabular-nums">{price}</span>
                <span className="text-muted-foreground -translate-y-1 text-sm font-medium">/月</span>
              </>
            )}
          </div>
        </section>

        {/* 操作区 */}
        <section className="mt-5 shrink-0" aria-label="选择版本">
          {cta === "current" ? (
            <Button
              type="button"
              variant="outline"
              className="h-11 w-full rounded-xl border-2 border-border bg-background disabled:opacity-100 font-bold"
              disabled
            >
              当前订阅
            </Button>
          ) : cta === "contact" ? (
            <Button
              type="button"
              className="h-11 w-full rounded-xl shadow-md shadow-primary/20 transition-shadow font-bold"
              onClick={() => onContact?.()}
            >
              联系销售
            </Button>
          ) : (
            <Button
              type="button"
              className="h-11 w-full rounded-xl shadow-md shadow-primary/20 transition-shadow font-bold"
              disabled={selecting}
              onClick={() => onSelect?.(plan, cycle)}
            >
              {selecting ? "创建订单…" : selectLabel}
            </Button>
          )}
        </section>

        {/* 权益区 */}
        <section className="border-border mt-5 flex min-h-0 flex-1 flex-col border-t pt-5" aria-label="计划限制">
          <p className="shrink-0 text-sm font-semibold">版本限制</p>
          <ul className="mt-3 space-y-2.5">
            {planCardLimits(plan).map((limit) => (
              <li key={limit.key} className="flex items-start justify-between gap-3 text-sm">
                <span className="inline-flex min-w-0 items-center gap-2">
                  <span
                    className="flex size-6 shrink-0 items-center justify-center rounded-full transition-colors duration-500 group-hover:bg-primary/10"
                    aria-hidden
                  >
                    <Check className="text-primary size-3.5" />
                  </span>
                  <span className="text-foreground font-medium">{limit.label}</span>
                </span>
                <span className="text-muted-foreground font-medium shrink-0 tabular-nums">{limit.value}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </article>
  );
}

function PlanComparisonTable({ plans }: { plans: PlanCatalogItem[] }) {
  const rows = planComparisonRows(plans);

  return (
    <section className="relative z-10 w-full max-w-6xl" aria-labelledby="plan-comparison-title">
      <header className="text-center">
        <h3 id="plan-comparison-title" className="text-2xl font-semibold tracking-tight sm:text-3xl">
          完整功能对比
        </h3>
        <p className="text-muted-foreground mt-2 text-sm font-medium sm:text-base">
          对比所有版本的限制与能力。
        </p>
      </header>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-border bg-muted-background shadow-sm">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-border border-b bg-background">
              <th className="px-5 py-4 text-left font-semibold">
                <span className="inline-flex items-center gap-3 px-2">
                  <Boxes className="size-3.5 text-foreground" />
                  功能
                </span>
              </th>
              {plans.map((plan) => (
                <th key={plan.code} className="px-4 py-4 text-center font-semibold">
                  {plan.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-border border-b last:border-b-0">
                <th scope="row" className="text-foreground px-5 py-4 text-left font-medium">
                  <PlanFeatureLabel limitKey={row.key} label={row.label} description={row.description} />
                </th>
                {row.values.map((value, index) => {
                  const plan = plans[index];
                  return (
                    <td
                      key={plan.code}
                      className="text-muted-foreground px-4 py-4 text-center font-medium tabular-nums"
                    >
                      {value}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

type SubscriptionPlanViewProps = {
  /** 覆盖内容区内边距等，供门闸页收紧左右留白 */
  contentClassName?: string;
  /** 插入内容区顶部（与定价卡片同列对齐），背景仍铺满整页 */
  topSlot?: ReactNode;
};

/** 订阅计划 · 定价卡片 */
export function SubscriptionPlanView({ contentClassName, topSlot }: SubscriptionPlanViewProps) {
  const [cycleOverride, setCycleOverride] = useState<BillingCycle | null>(null);
  const [selectingPlan, setSelectingPlan] = useState<string | null>(null);
  const [pendingChange, setPendingChange] = useState<{
    plan: PlanCatalogItem;
    cycle: BillingCycle;
    kind: "upgrade" | "downgrade";
    copy: PlanChangeConfirmCopy;
  } | null>(null);
  const [payOrder, setPayOrder] = useState<{
    id: string;
    amount_cents: number;
    changeKind: PlanChangeKind;
  } | null>(null);
  const [contactOpen, setContactOpen] = useState(false);
  const { data: catalog, isPending: catalogPending } = usePlanCatalog();
  const { data: subscription, isPending: subscriptionPending } = useTenantSubscription();
  const { data: platformCatalog = [], isPending: platformCatalogPending } = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
    ...sessionCatalogQueryOptions,
  });
  const plans = catalog?.plans ?? [];
  const billingCycles = catalog?.billing_cycles ?? [];
  const isPending = catalogPending || subscriptionPending;
  const cycle = cycleOverride ?? subscription?.billing_cycle ?? billingCycles[0]?.id ?? "monthly";
  const currentPlanCode = subscription?.plan_code ?? null;
  const currentBillingCycle = subscription?.billing_cycle ?? null;
  const subscriptionActive = isSubscriptionActive(subscription);

  async function createAndPay(plan: PlanCatalogItem, selectedCycle: BillingCycle, changeKind: PlanChangeKind) {
    if (!plan.orderable) return false;
    setSelectingPlan(plan.code);
    try {
      const order = await createSubscriptionOrder({
        plan_code: plan.code,
        billing_cycle: selectedCycle,
      });
      setPayOrder({ id: order.id, amount_cents: order.amount_cents, changeKind });
      return true;
    } catch (error) {
      toast.error(formatApiError(error, "创建订单失败"));
      return false;
    } finally {
      setSelectingPlan(null);
    }
  }

  function handleSelectPlan(plan: PlanCatalogItem, selectedCycle: BillingCycle) {
    if (!plan.orderable) return;
    const kind = resolvePlanChangeKind(plans, currentPlanCode, plan.code, { subscriptionActive });
    if (kind === "upgrade" || kind === "downgrade") {
      const currentPlanName =
        plans.find((item) => item.code === currentPlanCode)?.name ||
        subscription?.plan_name ||
        "当前计划";
      const periodEndLabel = subscription?.current_period_end
        ? formatBillingDate(subscription.current_period_end)
        : "当前账期末";
      setPendingChange({
        plan,
        cycle: selectedCycle,
        kind,
        copy: planChangeConfirmCopy({
          kind,
          targetPlanName: plan.name,
          currentPlanName,
          periodEndLabel,
        }),
      });
      return;
    }
    void createAndPay(plan, selectedCycle, kind);
  }

  async function handleConfirmPlanChange() {
    if (!pendingChange) return;
    const { plan, cycle: selectedCycle, kind } = pendingChange;
    const ok = await createAndPay(plan, selectedCycle, kind);
    if (ok) setPendingChange(null);
  }

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

      <div
        className={cn(
          "relative flex flex-col items-center gap-8 px-4 py-10 sm:px-6 lg:py-12",
          contentClassName,
        )}
      >
        {topSlot ? <div className="relative z-10 w-full max-w-6xl">{topSlot}</div> : null}
        <div className="relative w-full py-2 sm:py-4">
          <div
            aria-hidden
            className="pointer-events-none absolute -inset-x-12 -top-32 -bottom-32 sm:-inset-x-20 sm:-top-40 sm:-bottom-40"
            style={{
              background:
                "radial-gradient(ellipse 88% 64% at 50% 50%, color-mix(in srgb, var(--primary) 20%, transparent) 0%, color-mix(in srgb, var(--primary) 11%, transparent) 28%, color-mix(in srgb, var(--primary) 4%, transparent) 50%, transparent 72%)",
              maskImage:
                "radial-gradient(ellipse 100% 100% at 50% 50%, black 0%, black 36%, rgb(0 0 0 / 0.35) 52%, transparent 74%)",
              WebkitMaskImage:
                "radial-gradient(ellipse 100% 100% at 50% 50%, black 0%, black 36%, rgb(0 0 0 / 0.35) 52%, transparent 74%)",
            }}
          />
          <header className="relative z-10 mx-auto max-w-2xl text-center">
            <TextBadge variant="primary" className="px-4 py-1 text-sm font-semibold bg-primary text-primary-foreground">
              定价方案
            </TextBadge>
            {platformCatalogPending ? (
              <div
                className="mt-4 flex flex-wrap items-center justify-center gap-2.5"
                aria-busy
                aria-label="加载 AI 平台"
              >
                {Array.from({ length: PLATFORM_LOGO_SKELETON_COUNT }, (_, index) => (
                  <Skeleton key={index} className="size-8 rounded-md" aria-hidden />
                ))}
              </div>
            ) : platformCatalog.length > 0 ? (
              <div
                className="mt-4 flex flex-wrap items-center justify-center gap-2.5"
                role="img"
                aria-label={`支持 ${platformCatalog.length} 个 AI 平台`}
              >
                {platformCatalog.map((platform) => (
                  <PlatformLogo
                    key={platform.platform}
                    provider={platform.platform}
                    label={platform.label}
                    className="size-8"
                  />
                ))}
              </div>
            ) : null}
            <p className="text-muted-foreground mt-2 text-sm font-medium leading-relaxed sm:text-base">
              覆盖国内主流 AI 平台，实时监控分析品牌在 AI 中的竞争表现。
            </p>
          </header>
        </div>

        <div className="relative z-10">
          {isPending ? (
            <div
              aria-hidden
              className="border-border inline-flex min-h-10 items-center gap-1 rounded-full border bg-background p-1 opacity-50"
            >
              {Array.from({ length: 3 }, (_, index) => (
                <span key={index} className="inline-block h-8 w-16 rounded-full bg-muted-background" />
              ))}
            </div>
          ) : (
            <BillingCycleToggle cycles={billingCycles} value={cycle} onChange={setCycleOverride} />
          )}
        </div>

        <div className="relative z-10 grid w-full max-w-6xl gap-4 md:grid-cols-2 xl:grid-cols-4">
          {isPending
            ? Array.from({ length: 4 }, (_, index) => <PlanCardSkeleton key={index} />)
            : plans.map((plan) => {
                const matching = isMatchingSubscriptionPlan(
                  plan,
                  currentPlanCode,
                  currentBillingCycle,
                  cycle,
                );
                const changeKind = resolvePlanChangeKind(plans, currentPlanCode, plan.code, {
                  subscriptionActive,
                });
                return (
                  <PlanCard
                    key={plan.code}
                    plan={plan}
                    cycle={cycle}
                    cta={resolvePlanCta(plan, currentPlanCode, currentBillingCycle, cycle, {
                      subscriptionActive,
                    })}
                    onSelect={handleSelectPlan}
                    onContact={() => setContactOpen(true)}
                    selecting={selectingPlan === plan.code}
                    highlightAsBound={!subscriptionActive && matching}
                    selectLabel={planSelectLabel(changeKind, {
                      matchingExpired: !subscriptionActive && matching,
                    })}
                  />
                );
              })}
        </div>

        {!isPending && plans.length > 0 ? <PlanComparisonTable plans={plans} /> : null}
      </div>

      <PlanChangeConfirmDialog
        open={pendingChange !== null}
        copy={pendingChange?.copy ?? null}
        submitting={selectingPlan !== null}
        onOpenChange={(open) => {
          if (!open) setPendingChange(null);
        }}
        onConfirm={() => {
          void handleConfirmPlanChange();
        }}
      />

      <ContactQrDialog
        open={contactOpen}
        onOpenChange={setContactOpen}
        title="联系销售"
        description="微信扫码添加销售顾问"
      />

      <PayOrderDialog
        orderId={payOrder?.id ?? null}
        amountCents={payOrder?.amount_cents ?? 0}
        open={payOrder !== null}
        onOpenChange={(open) => {
          if (!open) setPayOrder(null);
        }}
        title="订阅支付"
        description={planChangePayDescription(payOrder?.changeKind ?? "new")}
      />
    </div>
  );
}
