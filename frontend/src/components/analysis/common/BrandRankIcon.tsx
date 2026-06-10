import { FaviconImage } from "@/components/common/FaviconImage";
import { cn } from "@/lib/utils";

const DOMAIN_LABEL = /\.[a-z]{2,}/i;

type BrandRankIconSize = "sm" | "default" | "lg";
type BrandRankIconShape = "square" | "circle";

const SIZE_CONFIG = {
  sm: {
    box: "size-5",
    img: "[&_img]:size-5",
    faviconSize: 20,
    faviconClass: "size-5",
    iconClass: "size-3",
    letterText: "text-[9px]",
  },
  default: {
    box: "size-6",
    img: "[&_img]:size-6",
    faviconSize: 24,
    faviconClass: "size-6",
    iconClass: "size-3.5",
    letterText: "text-[10px]",
  },
  lg: {
    box: "size-7",
    img: "[&_img]:size-7",
    faviconSize: 28,
    faviconClass: "size-7",
    iconClass: "size-3.5",
    letterText: "text-[11px]",
  },
} as const;

function brandRankRoundedClass(shape: BrandRankIconShape): string {
  return shape === "circle" ? "rounded-full" : "rounded-md";
}

function brandRankFavicon(
  label: string,
  size: BrandRankIconSize = "default",
  shape: BrandRankIconShape = "square",
) {
  const config = SIZE_CONFIG[size];
  return (
    <FaviconImage
      domain={label}
      size={config.faviconSize}
      className={cn(config.faviconClass, brandRankRoundedClass(shape))}
      iconClassName={config.iconClass}
    />
  );
}

export function buildBrandRankIcon(
  label: string,
  size: BrandRankIconSize = "default",
  shape: BrandRankIconShape = "square",
): React.ReactNode | undefined {
  if (!DOMAIN_LABEL.test(label)) return undefined;
  return brandRankFavicon(label, size, shape);
}

type BrandRankIconProps = {
  label: string | null;
  icon?: React.ReactNode;
  size?: BrandRankIconSize;
  shape?: BrandRankIconShape;
};

/** 品牌排名图标：域名 favicon 或首字母占位，与 AnalysisRankTable 一致 */
export function BrandRankIcon({
  label,
  icon,
  size = "default",
  shape = "square",
}: BrandRankIconProps) {
  const config = SIZE_CONFIG[size];
  const roundedClass = brandRankRoundedClass(shape);

  if (!label) {
    return <span className="font-medium">-</span>;
  }

  const resolvedIcon = icon ?? buildBrandRankIcon(label, size, shape);

  if (resolvedIcon) {
    return (
      <span
        className={cn(
          "inline-flex shrink-0 items-center justify-center",
          shape === "circle" && "overflow-hidden rounded-full",
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
        "bg-muted text-muted-foreground flex shrink-0 items-center justify-center font-semibold",
        roundedClass,
        config.box,
        config.letterText,
      )}
    >
      {label.slice(0, 1).toUpperCase()}
    </span>
  );
}
