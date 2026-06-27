import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, ChevronsUpDown, Plus } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import { Button } from "@/components/ui/button";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { DASHBOARD_SETUP_PATH } from "@/lib/dashboard";
import { clearSetupCache } from "@/lib/setup";
import { subjectDisplayLabel, subjectFaviconUrl } from "@/lib/subject";
import { cn } from "@/lib/utils";

export function SubjectSwitcher() {
  const navigate = useNavigate();
  const { subject, subjects, setActiveSubjectId } = useDashboardContext();
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

  const activeFaviconUrl = subjectFaviconUrl(subject);

  return (
    <div ref={rootRef} className="relative flex items-center pl-4">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((v) => !v)}
        className="hover:bg-background/80 flex min-w-0 max-w-[min(100vw-12rem,16rem)] items-center gap-2 rounded-md px-1.5 py-1 outline-hidden"
      >
        {activeFaviconUrl ? (
          <FaviconImage
            url={activeFaviconUrl}
            size={24}
            className="size-6 shrink-0"
            iconClassName="size-6"
          />
        ) : (
          <span className="bg-background text-muted-foreground flex size-6 shrink-0 items-center justify-center rounded text-xs font-semibold">
            {subjectDisplayLabel(subject).slice(0, 1).toUpperCase()}
          </span>
        )}
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
              const faviconUrl = subjectFaviconUrl(item);
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
                  {faviconUrl ? (
                    <FaviconImage
                      url={faviconUrl}
                      size={20}
                      className="size-5 shrink-0"
                      iconClassName="size-5"
                    />
                  ) : (
                    <span className="bg-background text-muted-foreground flex size-5 shrink-0 items-center justify-center rounded text-[10px] font-semibold">
                      {subjectDisplayLabel(item).slice(0, 1).toUpperCase()}
                    </span>
                  )}
                  <span className="min-w-0 flex-1 truncate font-medium">{subjectDisplayLabel(item)}</span>
                  {active ? <Check className="size-4 shrink-0" aria-hidden /> : null}
                </button>
              );
            })}
          </div>
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
        </div>
      ) : null}
    </div>
  );
}
