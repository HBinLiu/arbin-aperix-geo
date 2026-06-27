import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";

import { BILLING_TABS, billingTabPath } from "@/lib/billing/nav";
import type { BillingTab } from "@/types";
import { cn } from "@/lib/utils";

type BillingTabsProps = {
  value: BillingTab;
  className?: string;
  /** 嵌入 MainShell 顶栏时使用，不重复渲染底部分割线。 */
  embedded?: boolean;
};

/** 订阅与账单 Tab：订阅计划 / 账单明细 */
export function BillingTabs({ value, className, embedded = false }: BillingTabsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef(new Map<BillingTab, HTMLAnchorElement>());
  const [hoverId, setHoverId] = useState<BillingTab | null>(null);
  const [indicator, setIndicator] = useState({ left: 0, width: 0 });

  const indicatorTarget = hoverId ?? value;

  const updateIndicator = useCallback(() => {
    const container = containerRef.current;
    const tab = tabRefs.current.get(indicatorTarget);
    if (!container || !tab) return;

    const containerRect = container.getBoundingClientRect();
    const tabRect = tab.getBoundingClientRect();
    setIndicator({
      left: tabRect.left - containerRect.left + container.scrollLeft,
      width: tabRect.width,
    });
  }, [indicatorTarget]);

  useLayoutEffect(() => {
    updateIndicator();
  }, [updateIndicator, value]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(updateIndicator);
    observer.observe(container);
    for (const tab of tabRefs.current.values()) {
      observer.observe(tab);
    }

    window.addEventListener("resize", updateIndicator);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateIndicator);
    };
  }, [updateIndicator]);

  const tabList = (
    <div
      ref={containerRef}
      className={cn(
        "relative flex min-w-0 flex-wrap items-center",
        embedded && "h-full min-w-0 flex-1",
        className,
      )}
      role="tablist"
      onMouseLeave={() => setHoverId(null)}
    >
      {BILLING_TABS.map((tab) => (
        <NavLink
          key={tab.id}
          to={billingTabPath(tab.id)}
          ref={(node) => {
            if (node) tabRefs.current.set(tab.id, node);
            else tabRefs.current.delete(tab.id);
          }}
          role="tab"
          aria-selected={value === tab.id}
          onMouseEnter={() => setHoverId(tab.id)}
          className={({ isActive }) =>
            cn(
              "relative z-10 shrink-0 px-4 py-2.5 text-sm transition-colors",
              isActive ? "text-primary font-semibold" : "text-foreground font-medium",
            )
          }
        >
          {tab.label}
        </NavLink>
      ))}
      <span
        aria-hidden
        className="bg-primary pointer-events-none absolute bottom-0 h-0.5 transition-[left,width] duration-300 ease-out"
        style={{ left: indicator.left, width: indicator.width }}
      />
    </div>
  );

  if (embedded) return tabList;

  return <div className="border-border border-b">{tabList}</div>;
}
