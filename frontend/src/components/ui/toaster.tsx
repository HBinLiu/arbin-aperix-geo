import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

import { subscribeToasts, toast } from "@/lib/toast";
import type { ToastItem, ToastType } from "@/types";
import { cn } from "@/lib/utils";

const TYPE_STYLES: Record<
  ToastType,
  {
    icon: typeof AlertCircle;
    card: string;
    iconClass: string;
    titleClass: string;
    messageClass: string;
    title: string;
  }
> = {
  error: {
    icon: AlertCircle,
    card: "border-error/50 bg-error/10 shadow-[0_8px_24px_rgb(220_38_38/0.18)]",
    iconClass: "text-error",
    titleClass: "text-error",
    messageClass: "text-error/90",
    title: "请求失败",
  },
  success: {
    icon: CheckCircle2,
    card: "border-emerald-500/30 bg-emerald-50",
    iconClass: "text-emerald-600",
    titleClass: "text-foreground",
    messageClass: "text-muted-foreground",
    title: "操作成功",
  },
  info: {
    icon: Info,
    card: "border-primary/30 bg-accent",
    iconClass: "text-primary",
    titleClass: "text-foreground",
    messageClass: "text-muted-foreground",
    title: "提示",
  },
};

function ToastCard({ item, index }: { item: ToastItem; index: number }) {
  const style = TYPE_STYLES[item.type];
  const Icon = style.icon;

  return (
    <div
      role="alert"
      className={cn(
        "toast-slide-in flex w-full max-w-sm gap-3 rounded-lg border p-4",
        item.type === "error" ? style.card : cn("border-border bg-muted-background shadow-lg", style.card),
      )}
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <Icon className={cn("mt-0.5 size-5 shrink-0", style.iconClass)} aria-hidden />
      <div className="min-w-0 flex-1 text-left">
        <p className={cn("text-sm font-semibold", style.titleClass)}>{style.title}</p>
        <p className={cn("mt-1 text-sm leading-relaxed break-words", style.messageClass)}>{item.message}</p>
      </div>
      <button
        type="button"
        className={cn(
          "-mr-1 shrink-0 rounded p-1 transition-colors",
          item.type === "error"
            ? "text-error/70 hover:bg-error/10 hover:text-error"
            : "text-muted-foreground hover:text-foreground",
        )}
        aria-label="关闭提示"
        onClick={() => toast.dismiss(item.id)}
      >
        <X className="size-4" aria-hidden />
      </button>
    </div>
  );
}

export function Toaster() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => subscribeToasts(setItems), []);

  if (items.length === 0) return null;

  return createPortal(
    <div
      className="pointer-events-none fixed right-4 bottom-4 z-[200] flex w-[min(100vw-2rem,24rem)] flex-col gap-2"
      aria-live="polite"
      aria-relevant="additions"
    >
      {items.map((item, index) => (
        <div key={item.id} className="pointer-events-auto">
          <ToastCard item={item} index={index} />
        </div>
      ))}
    </div>,
    document.body,
  );
}
