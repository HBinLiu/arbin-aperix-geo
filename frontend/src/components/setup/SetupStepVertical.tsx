import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export type SetupStepVerticalProps = {
  steps: string[];
  currentStep: number;
};

/** 右侧竖向步骤条（对齐 onboard01.html：font-mono、圆点/竖线、当前步 shiny + spinner） */
export function SetupStepVertical({ steps, currentStep }: SetupStepVerticalProps) {
  return (
    <nav className="w-full" aria-label="设置流程">
      <ol className="flex flex-col">
        {steps.map((label, i) => {
          const isActive = i === currentStep;
          const isPast = i < currentStep;
          const isLast = i === steps.length - 1;

          return (
            <li key={label} className="flex min-h-14 gap-2">
              <div className="flex w-5 shrink-0 flex-col items-center">
                <div className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-transparent">
                  {isActive ? (
                    <Loader2 className="text-primary h-3 w-3 animate-spin" aria-hidden />
                  ) : (
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full transition-colors",
                        isPast ? "bg-primary" : "bg-muted-foreground/40",
                      )}
                      aria-hidden
                    />
                  )}
                </div>
                {!isLast ? (
                  <div
                    className={cn("my-1 w-px flex-1", isPast || isActive ? "bg-primary" : "bg-border")}
                    aria-hidden
                  />
                ) : null}
              </div>
              <div className="flex flex-1 items-start pt-0.5">
                <span
                  className={cn(
                    "font-mono text-sm leading-5 transition-colors",
                    isActive && "setup-step-active text-primary font-bold",
                    !isActive && isPast && "text-primary",
                    !isActive && !isPast && "text-foreground",
                  )}
                >
                  {label}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
