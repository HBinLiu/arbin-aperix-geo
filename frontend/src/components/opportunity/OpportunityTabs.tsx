import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";

import { OPPORTUNITY_TABS, opportunityTabPath } from "@/lib/opportunity/nav";
import type { OpportunityTab } from "@/types";
import { cn } from "@/lib/utils";

type OpportunityTabsProps = {
  value: OpportunityTab;
  className?: string;
  /** 嵌入 MainShell 顶栏时使用，不重复渲染底部分割线。 */
  embedded?: boolean;
};

/** 机会页 Tab：引用信源 / 潜在竞品 / 潜在提示词 */
export function OpportunityTabs({ value, className, embedded = false }: OpportunityTabsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef(new Map<OpportunityTab, HTMLAnchorElement>());
  const [hoverId, setHoverId] = useState<OpportunityTab | null>(null);
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
      {OPPORTUNITY_TABS.map((tab) => (
        <NavLink
          key={tab.id}
          to={opportunityTabPath(tab.id)}
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
