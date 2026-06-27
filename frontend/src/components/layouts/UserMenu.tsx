import { useEffect, useLayoutEffect, useRef, useState, type ComponentType, type MouseEventHandler, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  LogOut,
  Moon,
  Settings,
  Sun,
} from "lucide-react";

import { UserAvatar } from "@/components/user/UserAvatar";

import { clearStoredToken } from "@/api/client";
import { ProgressBar } from "@/components/common/ProgressBar";
import { useTheme } from "@/hooks/useTheme";
import { userPrimaryLabel, userSecondaryLabel } from "@/lib/auth";
import { dashboardNavToPath } from "@/lib/dashboard";
import { cn } from "@/lib/utils";
import type { User } from "@/types";

import { PROMPT_QUOTA_LIMIT } from "@/lib/prompt";
const CREDIT_QUOTA_LIMIT = 24000;
const MENU_PANEL_CLASS = "border-border w-72 overflow-hidden rounded-lg border bg-muted-background py-1 shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.18)]";
const MENU_OFFSET = 5;

type UserMenuProps = {
  user?: User;
  promptUsed?: number;
  creditUsed?: number;
};

function MenuDivider() {
  return <div className="border-border border-t" />;
}

function MenuRow({
  label,
  icon: Icon,
  onClick,
  primary = false,
  trailing,
}: {
  label: string;
  icon?: ComponentType<{ className?: string }>;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  primary?: boolean;
  trailing?: ReactNode;
}) {
  const interactive = Boolean(onClick);

  return (
    <div className="px-2 py-1">
      <button
        type="button"
        onClick={onClick}
        disabled={!interactive}
        className={cn(
          "flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-sm cursor-pointer",
          primary ? "text-primary hover:bg-primary/5" : "text-foreground hover:bg-foreground/5",
        )}
      >
        <span className="min-w-0 flex-1 font-medium">{label}</span>
        {trailing ?? (Icon ? (
          <Icon
            className={cn("size-4 shrink-0", primary ? "text-primary" : "text-muted-foreground")}
            aria-hidden
          />
        ) : null)}
      </button>
    </div>
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
    <div className="px-5 py-2.5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
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
  const navigate = useNavigate();
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
        <UserAvatar size="md" seed={user?.id} />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{primary}</p>
          {secondary ? (
            <p className="text-muted-foreground truncate text-xs">{secondary}</p>
          ) : null}
        </div>
      </div>

      <MenuDivider />
      <MenuRow
        label="设置"
        icon={Settings}
        onClick={() => {
          setOpen(false);
          navigate(dashboardNavToPath("profile"));
        }}
      />
      <MenuRow
        label="主题"
        icon={ThemeIcon}
        onClick={(event) => cycleTheme({ x: event.clientX, y: event.clientY })}
      />

      <MenuDivider />
      <UsageRow label="提示词" used={promptUsed} limit={PROMPT_QUOTA_LIMIT} />
      <UsageRow label="Token额度" used={creditUsed} limit={CREDIT_QUOTA_LIMIT} />

      <MenuDivider />
      <MenuRow label="退出登录" icon={LogOut} primary onClick={onLogout} />
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
        className="hover:bg-background/80 inline-flex items-center justify-center rounded-md p-1 outline-hidden"
      >
        <UserAvatar seed={user?.id} />
      </button>

      {open && typeof document !== "undefined"
        ? createPortal(menuPanel, document.body)
        : null}
    </div>
  );
}
