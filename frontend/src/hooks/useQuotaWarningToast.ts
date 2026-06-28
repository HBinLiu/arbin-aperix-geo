import { useEffect, useRef } from "react";

import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import {
  computeQuotaWarning,
  quotaWarningMessage,
  quotaWarningStorageKey,
} from "@/lib/billing/quota";
import { toast } from "@/lib/toast";

/** 站内 Toast：AI 额度 20% / 5% / 0% 阈值提醒（每周期每档一次）。 */
export function useQuotaWarningToast() {
  const { data: subscription } = useTenantSubscription();
  const shownRef = useRef<string | null>(null);

  useEffect(() => {
    if (!subscription) return;
    const code = computeQuotaWarning(subscription);
    if (!code) return;

    const storageKey = quotaWarningStorageKey(subscription, code);
    if (shownRef.current === storageKey) return;
    if (typeof window !== "undefined" && window.localStorage.getItem(storageKey) === "1") {
      shownRef.current = storageKey;
      return;
    }

    const message = quotaWarningMessage(code, subscription.usage.ai_requests_available);
    if (code === "0pct") {
      toast.error(message);
    } else {
      toast.info(message);
    }

    shownRef.current = storageKey;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(storageKey, "1");
    }
  }, [subscription]);
}
