import * as React from "react";
import { Link } from "react-router-dom";

import { AppLogo } from "@/components/common/AppLogo";

export type AuthShellProps = {
  /** 右侧主标题，如「登录 Aperix AI」 */
  title: string;
  /** 标题下说明文案 */
  description?: React.ReactNode;
  children: React.ReactNode;
};

/**
 * 鉴权页外壳：大屏左侧品牌区（背景图 + 标语），右侧表单。
 */
export function AuthShell({ title, description, children }: AuthShellProps) {
  return (
    <div className="flex min-h-svh flex-col overflow-y-auto bg-muted-background lg:flex-row">
      <main className="flex flex-1 flex-col justify-center px-5 py-10 sm:px-8 lg:px-14 xl:px-20">
        <div className="mx-auto w-full max-w-[400px]">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-[1.75rem] sm:leading-tight">{title}</h1>
          {description ? <div className="text-muted-foreground mt-2 text-sm leading-relaxed">{description}</div> : null}

          <div className="mt-8">{children}</div>

          <p className="text-muted-foreground mt-6 text-center text-[13px] leading-relaxed">
            继续操作即表示你已阅读、理解并同意平台{" "}
            <Link to="/terms" className="shrink-0 underline">
              使用条款
            </Link>
            {" "}与{" "}
            <Link to="/privacy" className="shrink-0 underline">
              隐私政策
            </Link>
            。
          </p>
        </div>
      </main>

      <aside className="hidden w-full p-3 lg:block lg:h-svh lg:w-1/2 lg:shrink-0">
        <div className="relative h-full overflow-hidden rounded-lg">
          <div
            className="auth-right-panel-bg bg-background absolute inset-0"
            style={{ backgroundImage: 'url("/assets/imgs/auth-light-bg.png")' }}
            aria-hidden
          />
          <div className="relative z-10 flex h-full items-center justify-center px-10 py-16">
            <div className="w-full max-w-[480px] space-y-8">
              <div className="text-foreground font-mono text-[clamp(2rem,3.2vw,2.75rem)] leading-[1.4] font-semibold tracking-tight">
                <p className="mb-0">
                  <span className="text-primary">Da</span>
                  <span>ta Driven</span>
                </p>
                <p className="mb-0">
                  <span className="text-primary">Gen</span>
                  <span>erative Engine</span>
                </p>
                <p className="mb-0">
                  <span className="text-primary">O</span>
                  <span>ptimization</span>
                </p>
              </div>

              <div className="border-foreground/10 border-t pt-4">
                <div className="flex items-center justify-between gap-4">
                  <Link to="/" className="flex items-center gap-2 transition-opacity hover:opacity-80">
                    <AppLogo width={24} height={24} className="size-6 object-contain" decoding="async" />
                    <span className="text-foreground text-sm font-semibold">Aperix AI</span>
                  </Link>
                  <Link to="/about" className="text-muted-foreground shrink-0 text-sm hover:underline">
                    联系我们
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
