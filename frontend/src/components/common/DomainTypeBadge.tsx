import { TextBadge } from "@/components/ui/badge";
import { domainTypeLabel } from "@/lib/domain-type";
import { cn } from "@/lib/utils";

type DomainTypeBadgeProps = {
  domainType: string | null | undefined;
  className?: string;
};

export function DomainTypeBadge({ domainType, className }: DomainTypeBadgeProps) {
  return (
    <TextBadge
      variant="gray"
      className={cn(
        "border-foreground/12 bg-transparent font-medium text-foreground",
        className,
      )}
    >
      {domainTypeLabel(domainType)}
    </TextBadge>
  );
}
