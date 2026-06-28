import { useLocation } from "react-router-dom";

import { BillingDetailsView } from "@/components/billing/BillingDetailsView";
import { SubscriptionPlanView } from "@/components/billing/SubscriptionPlanView";
import { billingTabFromPathname } from "@/lib/billing/nav";

/** 订阅与账单 · 订阅计划 / 账单明细 */
export function BillingContent() {
  const { pathname } = useLocation();
  const activeTab = billingTabFromPathname(pathname);

  if (activeTab === "plan") {
    return <SubscriptionPlanView />;
  }

  return <BillingDetailsView />;
}
