import { TextBadge } from "@/components/ui/badge";
import { urlTypeLabel } from "@/lib/url-type";
import { cn } from "@/lib/utils";

type UrlTypeBadgeProps = {
  urlType: string | null | undefined;
  className?: string;
};

export function UrlTypeBadge({ urlType, className }: UrlTypeBadgeProps) {
  return (
    <TextBadge
      variant="gray"
      className={cn(
        "border-foreground/12 bg-transparent font-medium text-foreground",
        className,
      )}
    >
      {urlTypeLabel(urlType)}
    </TextBadge>
  );
}
