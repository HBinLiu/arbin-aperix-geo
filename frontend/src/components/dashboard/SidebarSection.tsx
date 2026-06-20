import { SidebarNavItem } from "@/components/dashboard/SidebarNavItem";
import type { DashboardNavItem } from "@/types";

type SidebarSectionProps = {
  title: string;
  items: DashboardNavItem[];
  collapsed: boolean;
};

export function SidebarSection({ title, items, collapsed }: SidebarSectionProps) {
  return (
    <div className="space-y-1">
      {!collapsed ? (
        <p className="text-muted-foreground px-2.5 pb-1 text-xs font-normal tracking-wide">{title}</p>
      ) : null}
      {items.map((item) => (
        <SidebarNavItem key={item.id} item={item} collapsed={collapsed} />
      ))}
    </div>
  );
}
