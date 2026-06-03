import { BrandDetailSection } from "@/components/brand/BrandDetailSection";
import { CompetitorConfigSection } from "@/components/brand/CompetitorConfigSection";
import { PlatformConfigSection } from "@/components/brand/PlatformConfigSection";
import { PromptConfigSection } from "@/components/brand/PromptConfigSection";
import type { Subject } from "@/types";

type BrandPageProps = {
  subject: Subject;
};

/** 品牌配置页。 */
export function BrandPage({ subject }: BrandPageProps) {
  return (
    <div className="flex flex-col items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
      <BrandDetailSection subject={subject} />
      <PlatformConfigSection subject={subject} />
      <PromptConfigSection subjectId={subject.id} />
      <CompetitorConfigSection subjectId={subject.id} subjectType={subject.type} />
    </div>
  );
}
