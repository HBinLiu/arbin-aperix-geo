import { Settings2 } from "lucide-react";

import { BrandSectionCard } from "@/components/brand/BrandSectionCard";
import { toast } from "@/lib/toast";

type PromptConfigSectionProps = {
  subjectId: string;
};

export function PromptConfigSection({ subjectId: _subjectId }: PromptConfigSectionProps) {
  return (
    <BrandSectionCard
      title="提示词"
      description="引导 AI 分析与您的品牌或行业相关的内容。"
      actionLabel="管理提示词"
      actionVariant="default"
      actionIcon={<Settings2 className="size-4" aria-hidden />}
      onAction={() => toast.info("提示词管理功能即将推出")}
    />
  );
}
