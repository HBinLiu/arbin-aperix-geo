import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { mentionedBrandDisplayLabel } from "@/lib/brand/display";
import { brandIconFaviconLabel } from "@/lib/brand/iconColor";
import type { CitationMentionedBrand } from "@/types";

const VISIBLE_LIMIT = 5;

type MentionedBrandsCellProps = {
  brands: CitationMentionedBrand[];
};

/** 表格内叠放品牌 favicon，hover 展示完整列表 */
export function MentionedBrandsCell({ brands }: MentionedBrandsCellProps) {
  if (brands == null || brands.length === 0) {
    return "-";
  }

  const visible = brands.slice(0, VISIBLE_LIMIT);
  const overflow = brands.length - visible.length;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className="inline-flex cursor-default items-center rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          tabIndex={0}
          role="img"
          aria-label={`${brands.length} 个提及品牌`}
          onClick={(event) => event.stopPropagation()}
        >
          <span className="flex items-center -space-x-1">
            {visible.map((brand, index) => {
              const displayLabel = mentionedBrandDisplayLabel(brand);
              return (
                <span
                  key={`${displayLabel}-${brand.domain ?? index}`}
                  className="ring-background inline-flex rounded-full ring-2"
                >
                  <BrandRankIcon
                    label={brandIconFaviconLabel(displayLabel, brand.domain)}
                    size="sm"
                    shape="circle"
                  />
                </span>
              );
            })}
          </span>
          {overflow > 0 ? (
            <span className="text-muted-foreground ml-1 shrink-0 text-xs tabular-nums">
              +{overflow}
            </span>
          ) : null}
        </span>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        showArrow={false}
        className="border-border w-auto min-w-48 border bg-muted-background px-3 py-2.5 text-foreground shadow-lg"
      >
        <ul className="flex max-h-60 flex-col gap-2 overflow-y-auto overscroll-contain pr-1">
          {brands.map((brand, index) => {
            const displayLabel = mentionedBrandDisplayLabel(brand);
            return (
              <li
                key={`${displayLabel}-${brand.domain ?? index}`}
                className="flex items-center gap-2"
              >
                <BrandRankIcon
                  label={brandIconFaviconLabel(displayLabel, brand.domain)}
                  size="sm"
                  shape="circle"
                />
                <span className="text-sm font-normal">{displayLabel}</span>
              </li>
            );
          })}
        </ul>
      </TooltipContent>
    </Tooltip>
  );
}
