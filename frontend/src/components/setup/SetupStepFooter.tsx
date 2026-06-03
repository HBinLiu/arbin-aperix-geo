import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SetupStepFooterProps = {
  step: number;
  busy: boolean;
  submitting: boolean;
  onBack: () => void;
};

export function SetupStepFooter({ step, busy, submitting, onBack }: SetupStepFooterProps) {
  if (busy) return null;

  const continueLabel = step === 3 ? (submitting ? "提交中…" : "完成设置") : busy ? "分析中…" : "继续";

  return (
    <div className={cn("flex shrink-0 items-center pt-10", step > 0 ? "justify-between" : "justify-end")}>
      {step > 0 ? (
        <Button
          type="button"
          variant="ghost"
          className="group text-muted-foreground h-10 gap-0 px-6 text-sm font-medium"
          onClick={onBack}
        >
          <ChevronLeft
            className="mr-1 size-4 transition-transform duration-200 group-hover:-translate-x-0.5"
            aria-hidden
          />
          <span>返回</span>
        </Button>
      ) : null}
      <Button
        type="submit"
        disabled={submitting || busy}
        className="group h-10 gap-0 rounded-lg px-6 text-sm font-medium shadow-none"
      >
        <span>{continueLabel}</span>
        {(step !== 3 || busy) && (
          <ChevronRight
            className="ml-1 size-4 transition-transform duration-200 group-hover:translate-x-0.5"
            aria-hidden
          />
        )}
      </Button>
    </div>
  );
}
