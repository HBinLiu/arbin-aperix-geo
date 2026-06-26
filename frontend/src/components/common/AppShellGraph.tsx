import { cn } from "@/lib/utils";

type AppShellGraphProps = {
  className?: string;
};

/** 工作区 / 主体列表加载失败 */
export function WorkspaceErrorGraph({ className }: AppShellGraphProps) {
  return (
    <svg
      viewBox="0 0 200 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shell-float mx-auto h-auto w-full max-w-[200px]", className)}
      aria-hidden
    >
      <ellipse cx="100" cy="148" rx="56" ry="8" className="fill-primary/10 shell-pulse-glow" />
      <rect x="44" y="36" width="112" height="88" rx="12" className="fill-muted-background stroke-border stroke-[1.5]" />
      <rect x="56" y="52" width="64" height="8" rx="4" className="fill-background" />
      <rect x="56" y="68" width="88" height="6" rx="3" className="fill-background/80" />
      <rect x="56" y="80" width="72" height="6" rx="3" className="fill-background/60" />
      <circle cx="132" cy="44" r="18" className="fill-error/10 stroke-error/40 stroke-[1.5]" />
      <path
        d="M126 44h12M132 38v12"
        className="stroke-error stroke-[2] shell-shake"
        strokeLinecap="round"
      />
      <g className="shell-drift">
        <path
          d="M28 72c8-12 20-18 32-12"
          className="stroke-primary/35 stroke-[1.5] stroke-dasharray-4 6"
          strokeLinecap="round"
        />
        <circle cx="24" cy="70" r="6" className="fill-primary/20 stroke-primary/50 stroke-[1.5]" />
      </g>
    </svg>
  );
}

/** 用户信息加载失败 */
export function ProfileErrorGraph({ className }: AppShellGraphProps) {
  return (
    <svg
      viewBox="0 0 200 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shell-float mx-auto h-auto w-full max-w-[200px]", className)}
      aria-hidden
    >
      <ellipse cx="100" cy="148" rx="52" ry="8" className="fill-primary/10 shell-pulse-glow" />
      <circle cx="100" cy="68" r="36" className="fill-muted-background stroke-border stroke-[1.5]" />
      <circle cx="100" cy="60" r="14" className="fill-background" />
      <path
        d="M68 96c6-14 20-22 32-22s26 8 32 22"
        className="stroke-background stroke-[1.5] fill-background/30"
        strokeLinecap="round"
      />
      <g className="shell-bounce-soft">
        <rect x="138" y="28" width="40" height="40" rx="10" className="fill-error/10 stroke-error/35 stroke-[1.5]" />
        <path d="M150 48h16M158 40v16" className="stroke-error stroke-[2]" strokeLinecap="round" />
      </g>
    </svg>
  );
}

/** 加载中 */
export function LoadingGraph({ className }: AppShellGraphProps) {
  return (
    <div className={cn("relative mx-auto size-28", className)} aria-hidden>
      <div className="border-primary/15 absolute inset-0 rounded-full border-2 shell-spin-slow" />
      <div className="border-primary/30 absolute inset-2 rounded-full border-2 border-t-primary shell-spin-reverse" />
      <div className="bg-primary/15 absolute inset-6 rounded-full blur-md shell-pulse-glow" />
      <div className="bg-primary absolute inset-9 rounded-full shadow-[0_0_24px_var(--primary-shadow-strong)]" />
    </div>
  );
}
