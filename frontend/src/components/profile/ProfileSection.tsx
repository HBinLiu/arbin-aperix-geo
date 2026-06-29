import type { ReactNode } from "react";

export function ProfileSection({
  title,
  headerAction,
  children,
}: {
  title: string;
  headerAction?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="border-border overflow-hidden rounded-lg border bg-muted-background shadow-xs">
      <header className="border-border flex items-center justify-between gap-3 border-b bg-background px-4 py-4">
        <h2 className="text-base font-semibold tracking-tight">{title}</h2>
        {headerAction ? <div className="shrink-0">{headerAction}</div> : null}
      </header>
      <div className="divide-border divide-y text-left">{children}</div>
    </section>
  );
}
