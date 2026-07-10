import { CircleQuestionMark } from "lucide-react";

import { ActionTooltip, ActionTooltipProvider } from "@/components/ui/tooltip";

type Props = {
  label: string;
  description: string;
};

export default function QuestionButton({ label, description }: Props) {
  return (
    <ActionTooltipProvider>
      <ActionTooltip label={description} className="pricing-tooltip-content--wide">
        <button type="button" className="pricing-comparison-help" aria-label={`了解${label}`}>
          <CircleQuestionMark size={16} aria-hidden />
        </button>
      </ActionTooltip>
    </ActionTooltipProvider>
  );
}
