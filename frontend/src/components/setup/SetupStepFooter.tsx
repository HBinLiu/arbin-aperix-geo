import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SetupStepFooterProps = {
  step: number;
  maxStep: number;
  busy: boolean;
  submitting: boolean;
  onBack: () => void;
};

export function SetupStepFooter({ step, maxStep, busy, submitting, onBack }: SetupStepFooterProps) {
  // 发现竞品 / 生成主题 / 生成提示词：主内容区已显示 Loader，隐藏底部栏
  if (busy && !submitting) return null;

  const continueLabel = step === maxStep ? (submitting ? "提交中…" : "完成设置") : "继续";

  return (
    <div className={cn("flex shrink-0 items-center pt-10", step > 0 ? "justify-between" : "justify-end")}>
      {step > 0 ? (
        <Button
          type="button"
          variant="ghost"
          className="group text-muted-foreground h-10 gap-0 px-6 text-sm font-medium"
          onClick={onBack}
          disabled={submitting}
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
        disabled={submitting}
        className="group h-10 gap-0 rounded-lg px-6 text-sm font-medium"
      >
        <span>{continueLabel}</span>
        {step !== maxStep ? (
          <ChevronRight
            className="ml-1 size-4 transition-transform duration-200 group-hover:translate-x-0.5"
            aria-hidden
          />
        ) : null}
      </Button>
    </div>
  );
}
