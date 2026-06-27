import { useLocation } from "react-router-dom";

import { SubscriptionPlanView } from "@/components/billing/SubscriptionPlanView";
import { billingTabFromPathname } from "@/lib/billing/nav";

const INVOICES_META = {
  title: "账单明细",
  description: "查看历史订单、发票与支付记录。",
  empty: "账单明细功能即将推出，敬请期待。",
} as const;

/** 订阅与账单 · 订阅计划 / 账单明细 */
export function BillingContent() {
  const { pathname } = useLocation();
  const activeTab = billingTabFromPathname(pathname);

  if (activeTab === "plan") {
    return <SubscriptionPlanView />;
  }

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{INVOICES_META.title}</h2>
          <p className="text-muted-foreground mt-1 max-w-4xl text-sm font-medium leading-relaxed">
            {INVOICES_META.description}
          </p>
        </header>

        <div className="border-border text-muted-foreground flex min-h-[240px] items-center justify-center rounded-lg border bg-muted-background px-6 py-10 text-sm">
          {INVOICES_META.empty}
        </div>
      </div>
    </div>
  );
}
