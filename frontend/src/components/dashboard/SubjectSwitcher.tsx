import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, ChevronsUpDown, Plus } from "lucide-react";

import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { FaviconImage } from "@/components/common/FaviconImage";
import { Button } from "@/components/ui/button";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import { isAtSubjectLimit } from "@/lib/billing/limits";
import { DASHBOARD_SETUP_PATH } from "@/lib/dashboard";
import { clearSetupCache } from "@/lib/setup";
import { subjectDisplayLabel, subjectFaviconUrl } from "@/lib/subject";
import type { Subject } from "@/types";
import { cn } from "@/lib/utils";

function SubjectIcon({ subject, size }: { subject: Subject; size: "sm" | "default" }) {
  const label = subjectDisplayLabel(subject);
  const faviconUrl = subjectFaviconUrl(subject);
  const px = size === "sm" ? 20 : 24;
  const box = size === "sm" ? "size-5" : "size-6";

  if (faviconUrl) {
    return (
      <FaviconImage
        url={faviconUrl}
        size={px}
        className={cn(box, "shrink-0 rounded-md")}
        iconClassName={box}
        fallbackLabel={label}
        showLoadingSpinner={false}
      />
    );
  }

  // 无网站 URL 时与筛选条等一致：按展示名稳定着色的文字图标
  return <BrandRankIcon label={label} size={size} faviconLoadingSpinner={false} />;
}

export function SubjectSwitcher() {
  const navigate = useNavigate();
  const { subject, subjects, setActiveSubjectId } = useDashboardContext();
  const { data: subscription } = useTenantSubscription();
  const atSubjectLimit = isAtSubjectLimit(subscription);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
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

  const onSelect = (id: string) => {
    if (id !== subject.id) setActiveSubjectId(id);
    setOpen(false);
  };

  const onCreateProject = () => {
    setOpen(false);
    clearSetupCache();
    navigate(DASHBOARD_SETUP_PATH);
  };

  return (
    <div ref={rootRef} className="relative flex items-center pl-4">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((v) => !v)}
        className="hover:bg-background/80 flex min-w-0 max-w-[min(100vw-12rem,16rem)] items-center gap-2 rounded-md px-1.5 py-1 outline-hidden"
      >
        <SubjectIcon subject={subject} size="default" />
        <span className="truncate text-sm font-semibold">{subjectDisplayLabel(subject)}</span>
        <ChevronsUpDown className="text-muted-foreground size-4 shrink-0" aria-hidden />
      </button>

      {open ? (
        <div
          role="listbox"
          aria-label="切换项目"
          className="border-border absolute left-4 top-full z-50 mt-1 w-[min(calc(100vw-2rem),16rem)] overflow-hidden rounded-lg border bg-muted-background py-1 shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.18)]"
        >
          <div className="max-h-64 overflow-y-auto p-2">
            {subjects.map((item) => {
              const active = item.id === subject.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => onSelect(item.id)}
                  className={cn(
                    "flex w-full min-w-0 items-center gap-2 rounded-md px-3 py-2 text-left text-sm",
                    active && "bg-background",
                  )}
                >
                  <SubjectIcon subject={item} size="sm" />
                  <span className="min-w-0 flex-1 truncate font-medium">{subjectDisplayLabel(item)}</span>
                  {active ? <Check className="size-4 shrink-0" aria-hidden /> : null}
                </button>
              );
            })}
          </div>
          {!atSubjectLimit ? (
            <div className="border-border border-t p-2">
              <Button
                type="button"
                variant="brandout"
                size="sm"
                onClick={onCreateProject}
                className="w-full"
              >
                <Plus className="size-4 shrink-0" aria-hidden />
                添加新品牌
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
