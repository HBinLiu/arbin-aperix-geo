import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import { Bell, CreditCard, Info, Megaphone, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useNotificationActions, useNotifications, useNotificationUnreadCount } from "@/hooks/useNotifications";
import { cn } from "@/lib/utils";
import type { NotificationCategory, UserNotification } from "@/types/notifications";

const HEADER_ICON_BTN_CLASS = "border-border bg-muted-background size-8 rounded-md border";

const CATEGORY_ICON: Record<NotificationCategory, typeof Bell> = {
  billing: CreditCard,
  pipeline: Sparkles,
  subscription: CreditCard,
  system: Megaphone,
};

function NotificationItem({
  item,
  onOpen,
}: {
  item: UserNotification;
  onOpen: (item: UserNotification) => void;
}) {
  const Icon = CATEGORY_ICON[item.category] ?? Info;
  const timeLabel = formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: zhCN });

  return (
    <button
      type="button"
      className={cn(
        "hover:bg-foreground/5 flex w-full gap-3 rounded-md px-3 py-2.5 text-left transition-colors",
        !item.read && "bg-primary/5",
      )}
      onClick={() => onOpen(item)}
    >
      <span
        className={cn(
          "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md",
          item.category === "billing" ? "bg-amber-500/10 text-amber-600" : "bg-primary/10 text-primary",
        )}
      >
        <Icon className="size-4" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-start justify-between gap-2">
          <span className={cn("text-sm leading-snug", !item.read ? "font-semibold" : "font-medium")}>{item.title}</span>
          {!item.read ? <span className="bg-primary mt-1.5 size-2 shrink-0 rounded-full" aria-hidden /> : null}
        </span>
        {item.body ? (
          <span className="text-muted-foreground mt-0.5 line-clamp-2 block text-xs leading-relaxed">{item.body}</span>
        ) : null}
        <span className="text-muted-foreground mt-1 block text-[11px]">{timeLabel}</span>
      </span>
    </button>
  );
}

export function Notification() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const { data: unreadCount = 0 } = useNotificationUnreadCount();
  const { data, isLoading } = useNotifications(open);
  const { markRead, markAllRead } = useNotificationActions();

  const handleOpenItem = (item: UserNotification) => {
    if (!item.read) {
      markRead.mutate(item.id);
    }
    if (item.action_url.startsWith("/")) {
      navigate(item.action_url);
      setOpen(false);
    }
  };

  const badge =
    unreadCount > 0 ? (
      <span className="bg-destructive text-destructive-foreground absolute -top-1 -right-1 flex min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-semibold leading-4">
        {unreadCount > 99 ? "99+" : unreadCount}
      </span>
    ) : null;

  return (
    <>
      <button
        type="button"
        className={cn(buttonVariants({ variant: "ghost", size: "icon" }), HEADER_ICON_BTN_CLASS, "relative")}
        aria-label={unreadCount > 0 ? `通知，${unreadCount} 条未读` : "通知"}
        onClick={() => setOpen(true)}
      >
        <Bell className="size-4" />
        {badge}
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md gap-0 p-0">
          <DialogBody className="p-0">
            <DialogHeader className="border-border items-center border-b px-4 py-3">
              <DialogTitle>通知</DialogTitle>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-xs"
                  disabled={unreadCount === 0 || markAllRead.isPending}
                  onClick={() => markAllRead.mutate()}
                >
                  全部已读
                </Button>
                <DialogClose />
              </div>
            </DialogHeader>
            <div className="max-h-[min(60vh,420px)] overflow-y-auto p-2">
              {isLoading ? (
                <p className="text-muted-foreground px-3 py-8 text-center text-sm">加载中…</p>
              ) : !data?.items.length ? (
                <div className="flex flex-col items-center gap-2 px-3 py-10 text-center">
                  <Bell className="text-muted-foreground size-8 opacity-40" aria-hidden />
                  <p className="text-muted-foreground text-sm">暂无通知</p>
                </div>
              ) : (
                data.items.map((item) => (
                  <NotificationItem key={item.id} item={item} onOpen={handleOpenItem} />
                ))
              )}
            </div>
          </DialogBody>
        </DialogContent>
      </Dialog>
    </>
  );
}
