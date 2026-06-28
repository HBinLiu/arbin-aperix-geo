import type { ReactNode } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Gem, QrCode } from "lucide-react";

import { fetchMe } from "@/api/auth";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Notification } from "@/components/layouts/Notification";
import { UserMenu } from "@/components/layouts/UserMenu";
import { AppLogo } from "@/components/common/AppLogo";
import { dashboardNavToPath } from "@/lib/dashboard";
import { queryKeys } from "@/lib/queries";

export const HEADER_ICON_BTN_CLASS = "border-border bg-muted-background size-8 rounded-md border";

type AppShellProps = {
  children: ReactNode;
  headerStart?: ReactNode;
};

/**
 * 控制台应用外壳（顶栏 + 内容卡片区）。
 */
export function AppShell({ children, headerStart }: AppShellProps) {
  const navigate = useNavigate();
  const [supportOpen, setSupportOpen] = useState(false);
  const { data: user } = useQuery({
    queryKey: queryKeys.me,
    queryFn: fetchMe,
    retry: false,
  });

  return (
    <div className="bg-background text-foreground flex h-svh flex-col overflow-hidden">
      <header className="relative z-50 flex h-12 w-full shrink-0 items-center justify-between pr-2.5">
        {headerStart ?? (
          <div className="flex items-center pl-2.5">
            <button
              type="button"
              onClick={() => navigate("/")}
              className="flex items-center gap-2 rounded-md px-2 py-1 outline-hidden hover:bg-accent/60"
            >
              <AppLogo width={24} height={24} className="size-6 object-contain" decoding="async" />
              <span className="text-foreground hidden text-sm font-semibold sm:inline">Aperix AI</span>
            </button>
          </div>
        )}
        <div className="ml-auto flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={HEADER_ICON_BTN_CLASS}
            aria-label="订阅与账单"
            onClick={() => navigate(dashboardNavToPath("billing"))}
          >
            <Gem className="size-4" />
          </Button>
          <Notification />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={HEADER_ICON_BTN_CLASS}
            aria-label="客服微信"
            onClick={() => setSupportOpen(true)}
          >
            <QrCode className="size-4" />
          </Button>
          <UserMenu user={user} />
        </div>
      </header>

      <Dialog open={supportOpen} onOpenChange={setSupportOpen}>
        <DialogContent className="max-w-xs">
          <DialogBody className="space-y-4 pb-5">
            <DialogHeader>
              <div>
                <DialogTitle>联系客服</DialogTitle>
              </div>
              <DialogClose />
            </DialogHeader>
            <div className="flex flex-col items-center gap-3">
              <img
                src="/customer.png"
                alt="客服微信二维码"
                width={220}
                height={220}
                className="size-[220px] rounded-lg object-contain"
                decoding="async"
              />
              <DialogDescription className="mt-0 text-center">扫码添加客服微信</DialogDescription>
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>

      <main className="flex min-h-0 min-w-0 w-full flex-1 bg-sidebar px-2.5 pb-2.5 pt-0">{children}</main>
    </div>
  );
}
