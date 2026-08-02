import { useQueryClient } from "@tanstack/react-query";
import { ChevronsUpDown, LogOut } from "lucide-react";

import { clearStoredToken } from "@/api/client";
import { SubscriptionPlanView } from "@/components/billing/SubscriptionPlanView";
import { UserAvatar } from "@/components/user/UserAvatar";
import { userPrimaryLabel } from "@/lib/auth";
import type { User } from "@/types";

type SubscriptionRequiredViewProps = {
  user: User;
};

/** 订阅失效门闸：整页为定价方案背景，顶部叠加用户栏。 */
export function SubscriptionRequiredView({ user }: SubscriptionRequiredViewProps) {
  const queryClient = useQueryClient();
  const primary = userPrimaryLabel(user);

  const onLogout = () => {
    clearStoredToken();
    queryClient.clear();
    window.location.replace("/auth/login");
  };

  return (
    <div className="bg-background text-foreground h-svh overflow-x-hidden overflow-y-auto">
      <SubscriptionPlanView
        contentClassName="px-2 pt-3 sm:px-3 sm:pt-4 lg:px-4 lg:pb-12"
        topSlot={
          <header className="border-border bg-muted-background flex min-h-14 items-center gap-3 rounded-xl border px-3 py-2.5 sm:gap-4 sm:px-4">
            <div className="flex min-w-0 items-center gap-2.5">
              <UserAvatar size="sm" seed={user.id} />
              <span className="truncate text-sm font-semibold">{primary}</span>
              <ChevronsUpDown className="text-muted-foreground size-3.5 shrink-0" aria-hidden />
            </div>

            <div className="min-w-0 flex-1 px-1 text-left sm:px-4">
              <p className="text-primary text-sm font-semibold leading-snug">需要有效订阅才能继续。</p>
              <p className="text-muted-foreground mt-0.5 text-xs leading-snug sm:text-sm">
                请先完成计划订阅。订阅前无法关闭此视图。
              </p>
            </div>

            <button
              type="button"
              aria-label="退出登录"
              onClick={onLogout}
              className="text-muted-foreground hover:text-foreground hover:bg-background/80 inline-flex size-9 shrink-0 items-center justify-center rounded-md transition-colors"
            >
              <LogOut className="size-4" aria-hidden />
            </button>
          </header>
        }
      />
    </div>
  );
}
