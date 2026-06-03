import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Bell, Gem, Headphones } from "lucide-react";

import { Button } from "@/components/ui/button";
import { userAvatarInitial, userDisplayName } from "@/lib/auth";
import type { User } from "@/types";
import { queryKeys } from "@/lib/queries";

export const HEADER_ICON_BTN_CLASS = "border-border bg-white size-8 rounded-md border";

type AppShellProps = {
  children: ReactNode;
  headerStart?: ReactNode;
};

/**
 * 控制台应用外壳（顶栏 + 内容卡片区）。
 */
export function AppShell({ children, headerStart }: AppShellProps) {
  const queryClient = useQueryClient();
  const cachedUser = queryClient.getQueryData<User>(queryKeys.me);
  const avatar = cachedUser ? userAvatarInitial(cachedUser) : "U";
  const name = cachedUser ? userDisplayName(cachedUser) : "用户";

  return (
    <div className="bg-app-sidebar text-foreground flex h-svh flex-col overflow-hidden">
      <header className="relative z-50 flex h-14 w-full shrink-0 items-center justify-between pr-2.5">
        {headerStart ?? (
          <div className="flex items-center pl-2.5">
            <Link to="/" className="flex items-center gap-2 rounded-md px-2 py-1 outline-hidden hover:bg-accent/60">
              <img src="/logo.png" alt="" width={24} height={24} className="size-6 object-contain" decoding="async" />
              <span className="text-foreground hidden text-sm font-semibold sm:inline">Aperix AI</span>
            </Link>
          </div>
        )}
        <div className="ml-auto flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={HEADER_ICON_BTN_CLASS}
            aria-label="会员"
          >
            <Gem className="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={HEADER_ICON_BTN_CLASS}
            aria-label="通知"
          >
            <Bell className="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={HEADER_ICON_BTN_CLASS}
            aria-label="支持"
          >
            <Headphones className="size-4" />
          </Button>
          <button
            type="button"
            className="hover:bg-muted/80 ml-1 flex items-center gap-2 rounded-md px-2 py-1 outline-hidden"
            aria-label="用户菜单"
          >
            <span className="bg-primary text-primary-foreground flex size-7 items-center justify-center rounded-full text-xs font-semibold">
              {avatar}
            </span>
            <span className="hidden text-sm font-medium sm:inline">{name}</span>
          </button>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 bg-sidebar px-2.5 pb-2.5 pt-0">{children}</main>
    </div>
  );
}
