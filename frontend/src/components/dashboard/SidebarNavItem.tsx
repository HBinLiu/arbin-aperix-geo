import { NavLink } from "react-router-dom";

import { dashboardNavToPath } from "@/lib/dashboard";
import type { DashboardNavItem } from "@/types";
import { cn } from "@/lib/utils";

type SidebarNavItemProps = {
  item: DashboardNavItem;
  collapsed: boolean;
};

export function SidebarNavItem({ item, collapsed }: SidebarNavItemProps) {
  const Icon = item.icon;
  return (
    <NavLink
      to={dashboardNavToPath(item.id)}
      end={item.id === "overview"}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          "flex h-9 w-full items-center rounded-md text-sm transition-colors",
          collapsed ? "justify-center px-0" : "gap-2.5 px-2.5",
          isActive
            ? "bg-primary/10 text-primary font-semibold"
            : "text-sidebar-nav hover:bg-muted/80 hover:text-foreground",
        )
      }
    >
      {({ isActive }) => (
        <>
          <span className="relative shrink-0">
            <Icon className="size-4" strokeWidth={isActive ? 2.5 : 2} aria-hidden />
            {collapsed && item.badge ? (
              <span className="bg-primary absolute -top-0.5 -right-0.5 size-1.5 rounded-full" aria-hidden />
            ) : null}
          </span>
          {!collapsed ? <span className="truncate">{item.label}</span> : null}
          {!collapsed && item.badge ? (
            <span className="bg-primary/10 text-primary ml-auto rounded px-1.5 py-0.5 text-[10px] font-semibold leading-none">
              {item.badge}
            </span>
          ) : null}
        </>
      )}
    </NavLink>
  );
}
