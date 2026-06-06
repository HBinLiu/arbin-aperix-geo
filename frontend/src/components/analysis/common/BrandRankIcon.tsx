import { FaviconImage } from "@/components/common/FaviconImage";
import { cn } from "@/lib/utils";

const DOMAIN_LABEL = /\.[a-z]{2,}/i;

type BrandRankIconSize = "sm" | "default" | "lg";

const SIZE_CONFIG = {
  sm: {
    box: "size-5",
    img: "[&_img]:size-5",
    faviconSize: 20,
    faviconClass: "size-5 rounded-md",
    iconClass: "size-3",
    letterText: "text-[9px]",
  },
  default: {
    box: "size-6",
    img: "[&_img]:size-6",
    faviconSize: 24,
    faviconClass: "size-6 rounded-md",
    iconClass: "size-3.5",
    letterText: "text-[10px]",
  },
  lg: {
    box: "size-7",
    img: "[&_img]:size-7",
    faviconSize: 28,
    faviconClass: "size-7 rounded-md",
    iconClass: "size-3.5",
    letterText: "text-[11px]",
  },
} as const;

function brandRankFavicon(label: string, size: BrandRankIconSize = "default") {
  const config = SIZE_CONFIG[size];
  return (
    <FaviconImage
      domain={label}
      size={config.faviconSize}
      className={config.faviconClass}
      iconClassName={config.iconClass}
    />
  );
}

export function buildBrandRankIcon(label: string, size: BrandRankIconSize = "default"): React.ReactNode | undefined {
  if (!DOMAIN_LABEL.test(label)) return undefined;
  return brandRankFavicon(label, size);
}

type BrandRankIconProps = {
  label: string | null;
  icon?: React.ReactNode;
  size?: BrandRankIconSize;
};

/** 品牌排名图标：域名 favicon 或首字母占位，与 AnalysisRankTable 一致 */
export function BrandRankIcon({ label, icon, size = "default" }: BrandRankIconProps) {
  const config = SIZE_CONFIG[size];

  if (!label) {
    return <span className="font-medium">-</span>;
  }

  const resolvedIcon = icon ?? buildBrandRankIcon(label, size);

  if (resolvedIcon) {
    return (
      <span
        className={cn(
          "inline-flex shrink-0 items-center justify-center",
          config.box,
          config.img,
        )}
      >
        {resolvedIcon}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "bg-muted text-muted-foreground flex shrink-0 items-center justify-center rounded-md font-semibold",
        config.box,
        config.letterText,
      )}
    >
      {label.slice(0, 1).toUpperCase()}
    </span>
  );
}
