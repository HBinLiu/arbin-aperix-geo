import { useEffect, useLayoutEffect, useRef, useState, type ComponentType, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  LogOut,
  Moon,
  Settings,
  Smile,
  Sun,
  Ticket,
  Wallet,
} from "lucide-react";

import { clearStoredToken } from "@/api/client";
import { ProgressBar } from "@/components/common/ProgressBar";
import { useTheme } from "@/hooks/useTheme";
import { userPrimaryLabel, userSecondaryLabel } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { User } from "@/types";

import { PROMPT_QUOTA_LIMIT } from "@/lib/prompt";
const CREDIT_QUOTA_LIMIT = 24000;
const MENU_PANEL_CLASS = "border-border w-72 overflow-hidden rounded-lg border bg-white py-1 shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.18)]";
const MENU_OFFSET = 5;

type UserMenuProps = {
  user?: User;
  promptUsed?: number;
  creditUsed?: number;
};

function UserAvatar({ size = "sm" }: { size?: "sm" | "md" }) {
  return (
    <span
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full bg-[#3d7aed] text-white",
        size === "sm" ? "size-7" : "size-9",
      )}
    >
      <Smile className={size === "sm" ? "size-4" : "size-5"} strokeWidth={2} aria-hidden />
    </span>
  );
}

function MenuDivider() {
  return <div className="border-border border-t" />;
}

function MenuRow({
  label,
  icon: Icon,
  onClick,
  destructive = false,
  trailing,
}: {
  label: string;
  icon?: ComponentType<{ className?: string }>;
  onClick?: () => void;
  destructive?: boolean;
  trailing?: ReactNode;
}) {
  const interactive = Boolean(onClick);

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      className={cn(
        "flex w-full items-center justify-between px-4 py-2.5 text-left text-sm transition-colors",
        interactive ? "hover:bg-muted/60" : "cursor-default",
        destructive ? "text-red-500" : "text-foreground",
      )}
    >
      <span>{label}</span>
      {trailing ?? (Icon ? (
        <Icon className={cn("size-4 shrink-0", destructive ? "text-red-500" : "text-muted-foreground")} />
      ) : null)}
    </button>
  );
}

function UsageRow({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number;
}) {
  return (
    <div className="px-4 py-2.5">
      <div className="flex items-center justify-between text-sm">
        <span>{label}</span>
        <span className="text-muted-foreground tabular-nums">
          {used}/{limit}
        </span>
      </div>
      <ProgressBar value={used} max={limit} className="mt-2" />
    </div>
  );
}

export function UserMenu({
  user,
  promptUsed = 0,
  creditUsed = 0,
}: UserMenuProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuStyle, setMenuStyle] = useState<{ top: number; right: number } | null>(null);
  const { theme, cycleTheme } = useTheme();

  const ThemeIcon = theme === "dark" ? Moon : Sun;

  useLayoutEffect(() => {
    if (!open || !rootRef.current) {
      setMenuStyle(null);
      return;
    }

    const update = () => {
      const trigger = rootRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      setMenuStyle({
        top: rect.bottom + MENU_OFFSET,
        right: window.innerWidth - rect.right,
      });
    };

    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const onLogout = () => {
    setOpen(false);
    clearStoredToken();
    queryClient.clear();
    window.location.replace("/auth/login");
  };

  const primary = user ? userPrimaryLabel(user) : "用户";
  const secondary = user ? userSecondaryLabel(user) : null;

  const menuPanel = (
    <div
      ref={menuRef}
      role="menu"
      aria-label="用户菜单"
      className={cn(
        MENU_PANEL_CLASS,
        "fixed z-[110]",
        !menuStyle && "pointer-events-none opacity-0",
      )}
      style={
        menuStyle
          ? { top: menuStyle.top, right: menuStyle.right }
          : { top: 0, right: 0 }
      }
    >
      <div className="flex items-center gap-3 px-4 py-4">
        <UserAvatar size="md" />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{primary}</p>
          {secondary ? (
            <p className="text-muted-foreground truncate text-xs">{secondary}</p>
          ) : null}
        </div>
      </div>

      <MenuDivider />
      <MenuRow label="设置" icon={Settings} />
      <MenuRow label="主题" icon={ThemeIcon} onClick={cycleTheme} />

      <MenuDivider />
      <UsageRow label="提示词" used={promptUsed} limit={PROMPT_QUOTA_LIMIT} />
      <UsageRow label="Token额度" used={creditUsed} limit={CREDIT_QUOTA_LIMIT} />

      <MenuDivider />
      <MenuRow label="订阅" icon={Ticket} />
      <MenuRow label="计划与账单" icon={Wallet} />

      <MenuDivider />
      <MenuRow label="退出登录" icon={LogOut} destructive onClick={onLogout} />
    </div>
  );

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="用户菜单"
        onClick={() => setOpen((value) => !value)}
        className="hover:bg-muted/80 rounded-md p-1 outline-hidden"
      >
        <UserAvatar />
      </button>

      {open && typeof document !== "undefined"
        ? createPortal(menuPanel, document.body)
        : null}
    </div>
  );
}
