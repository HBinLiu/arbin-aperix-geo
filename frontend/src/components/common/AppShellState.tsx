import { SETUP_LIGHT_BG } from "@/lib/assets/shell";
import type { ReactNode } from "react";
import { isAxiosError } from "axios";
import { Loader2, LogIn, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import { LoadingGraph, ProfileErrorGraph, WorkspaceErrorGraph } from "@/components/common/AppShellGraph";
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
      <div className="shell-fade-up w-full max-w-md">{children}</div>
    </div>
  );
}

function GraphFrame({
  children,
  backgroundImage,
}: {
  children: ReactNode;
  backgroundImage?: string;
}) {
  return (
    <div
      className={cn(
        "border-border/80 relative mb-6 overflow-hidden rounded-xl border bg-linear-to-b from-background/60 to-surface px-6 py-8",
        backgroundImage && "bg-cover bg-center bg-no-repeat",
      )}
      style={backgroundImage ? { backgroundImage: `url(${backgroundImage})` } : undefined}
    >
      {backgroundImage ? <div className="absolute inset-0 bg-muted-background/85 backdrop-blur-[2px]" aria-hidden /> : null}
      <div className="relative">{children}</div>
    </div>
  );
}

export function AppShellLoading({ message }: { message: string }) {
  return (
    <AppShell>
      <ShellStatePanel>
        <div className="p-6 sm:p-8">
          <GraphFrame backgroundImage={SETUP_LIGHT_BG}>
            <LoadingGraph />
          </GraphFrame>
          <div className="space-y-3 text-center">
            <p className="text-foreground text-lg font-semibold tracking-tight">{message}</p>
            <p className="text-muted-foreground text-sm leading-relaxed">正在同步您的数据，请稍候…</p>
            <div className="flex justify-center gap-1.5 pt-1" aria-hidden>
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="bg-primary size-1.5 rounded-full shell-bounce-soft"
                  style={{ animationDelay: `${i * 0.2}s` }}
                />
              ))}
            </div>
          </div>
        </div>
      </ShellStatePanel>
    </AppShell>
  );
}

export type AppShellErrorVariant = "workspace" | "profile";

type AppShellErrorProps = {
  variant?: AppShellErrorVariant;
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
  variant = "workspace",
  title,
  description,
  error,
  retrying,
  onRetry,
}: AppShellErrorProps) {
  const meta = resolveErrorMeta(error);
  const ErrorGraph = variant === "profile" ? ProfileErrorGraph : WorkspaceErrorGraph;

  return (
    <AppShell>
      <ShellStatePanel>
        <div className="p-6 sm:p-8">
          <GraphFrame>
            <ErrorGraph />
          </GraphFrame>

          <div className="space-y-4 text-center">
            <div className="space-y-2">
              <h2 className="text-foreground text-lg font-semibold tracking-tight sm:text-xl">{title}</h2>
              <p className="text-muted-foreground text-sm leading-relaxed">{description ?? meta.description}</p>
            </div>

            <div className="flex flex-col gap-2 pt-1 sm:flex-row sm:justify-center">
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
                  <Link to="/auth/login?next=%2Fapp">
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
        </div>
      </ShellStatePanel>
    </AppShell>
  );
}
