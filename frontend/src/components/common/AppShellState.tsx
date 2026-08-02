import type { ReactNode } from "react";
import { isAxiosError } from "axios";
import { Loader2, LogIn, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import { AppLogo } from "@/components/common/AppLogo";
import { AppShell } from "@/components/layouts/AppShell";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ShellStatePanelProps = {
  children: ReactNode;
  className?: string;
};

function ShellStatePanel({ children, className }: ShellStatePanelProps) {
  return (
    <div
      className={cn(
        "flex min-h-[min(32rem,calc(100svh-7rem))] flex-1 flex-col items-center justify-center p-6 sm:p-10",
        className,
      )}
    >
      <div className="shell-fade-up w-full max-w-sm">{children}</div>
    </div>
  );
}

function BrandMark({ pulse = false }: { pulse?: boolean }) {
  return (
    <AppLogo
      width={40}
      height={40}
      className={cn("size-10 object-contain", pulse && "shell-brand-breathe")}
      decoding="async"
      alt=""
      aria-hidden
    />
  );
}

export function AppShellLoading({ message }: { message: string }) {
  return (
    <AppShell>
      <ShellStatePanel>
        <div className="flex flex-col items-center gap-4 text-center" role="status" aria-live="polite">
          <BrandMark pulse />
          <p className="text-muted-foreground text-sm font-medium">{message}</p>
        </div>
      </ShellStatePanel>
    </AppShell>
  );
}

type AppShellErrorProps = {
  title: string;
  description?: string;
  error?: unknown;
  retrying?: boolean;
  onRetry: () => void;
};

function resolveErrorMeta(error: unknown): { description: string; showLogin: boolean } {
  if (isAxiosError(error)) {
    const status = error.response?.status;
    if (status === 401) {
      return {
        description: "登录状态可能已失效，请重新登录。具体原因请查看右下角提示。",
        showLogin: true,
      };
    }
    if (status === 403) {
      return {
        description: "当前账号暂无访问权限，请联系管理员。",
        showLogin: false,
      };
    }
    if (!error.response) {
      return {
        description: "暂时无法连接服务器，请检查网络后重试。",
        showLogin: false,
      };
    }
  }
  return {
    description: "加载失败，请您稍候再试试。",
    showLogin: false,
  };
}

export function AppShellError({
  title,
  description,
  error,
  retrying,
  onRetry,
}: AppShellErrorProps) {
  const meta = resolveErrorMeta(error);

  return (
    <AppShell>
      <ShellStatePanel>
        <div className="flex flex-col items-center gap-5 text-center">
          <BrandMark />
          <div className="space-y-2">
            <h2 className="text-foreground text-lg font-semibold tracking-tight sm:text-xl">{title}</h2>
            <p className="text-muted-foreground text-sm leading-relaxed">{description ?? meta.description}</p>
          </div>

          <div className="flex w-full flex-col gap-2 sm:flex-row sm:justify-center">
            <Button type="button" className="gap-2" disabled={retrying} onClick={onRetry}>
              {retrying ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <RefreshCw className="size-4" aria-hidden />
              )}
              {retrying ? "正在重试…" : "重新加载"}
            </Button>
            {meta.showLogin ? (
              <Button type="button" variant="outline" className="gap-2" asChild>
                <Link to="/auth/login?next=%2F">
                  <LogIn className="size-4" aria-hidden />
                  前往登录
                </Link>
              </Button>
            ) : (
              <Button type="button" variant="outline" asChild>
                <a href="/">返回官网</a>
              </Button>
            )}
          </div>
        </div>
      </ShellStatePanel>
    </AppShell>
  );
}
