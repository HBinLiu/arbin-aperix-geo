import { memo, useMemo, type CSSProperties, type ReactNode } from "react";
import { Globe } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import { brandIconColor } from "@/lib/brand/iconColor";
import { faviconUrlFromHost } from "@/lib/favicon";
import { cn } from "@/lib/utils";

const DOMAIN_LABEL = /\.[a-z]{2,}/i;

export type BrandRankIconSize = "xs" | "sm" | "default" | "lg";
export type BrandRankIconShape = "square" | "circle";

const SIZE_CONFIG = {
  xs: {
    box: "size-4",
    img: "[&_img]:size-4",
    faviconSize: 16,
    faviconClass: "size-4",
    iconClass: "size-2.5",
    letterText: "text-[9px]",
  },
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

function brandIconFillStyle(color: string): CSSProperties {
  return { backgroundColor: color, color: "#ffffff" };
}

function brandRankFavicon(
  label: string,
  size: BrandRankIconSize = "default",
  shape: BrandRankIconShape = "square",
  showLoadingSpinner = true,
) {
  const config = SIZE_CONFIG[size];
  return (
    <FaviconImage
      url={faviconUrlFromHost(label)}
      size={config.faviconSize}
      className={cn(config.faviconClass, brandRankRoundedClass(shape))}
      iconClassName={config.iconClass}
      showLoadingSpinner={showLoadingSpinner}
      fallbackLabel={label}
    />
  );
}

export type BrandRankIconProps = {
  /** favicon 解析用（通常为 domain）；无域名时用展示名首字母 */
  label: string | null;
  icon?: ReactNode;
  size?: BrandRankIconSize;
  shape?: BrandRankIconShape;
  className?: string;
  /** 为 false 时 favicon 加载不显示转圈（用于 FilterBar 等） */
  faviconLoadingSpinner?: boolean;
};

/** 品牌图标：有 favicon 时原样展示；无图标时首字母占位并按 label 着色 */
export const BrandRankIcon = memo(function BrandRankIcon({
  label,
  icon,
  size = "default",
  shape = "square",
  className,
  faviconLoadingSpinner = true,
}: BrandRankIconProps) {
  const config = SIZE_CONFIG[size];
  const roundedClass = brandRankRoundedClass(shape);
  const letterColor = useMemo(
    () => brandIconColor(label ?? ""),
    [label],
  );

  if (!label) {
    return (
      <span
        className={cn(
          "bg-background text-muted-foreground inline-flex shrink-0 items-center justify-center",
          shape === "circle" && "overflow-hidden rounded-full",
          roundedClass,
          config.box,
          className,
        )}
      >
        <Globe className={cn("shrink-0", config.faviconClass)} aria-hidden />
      </span>
    );
  }

  const resolvedIcon = icon ?? (
    DOMAIN_LABEL.test(label)
      ? brandRankFavicon(label, size, shape, faviconLoadingSpinner)
      : undefined
  );

  if (resolvedIcon) {
    return (
      <span
        className={cn(
          "inline-flex shrink-0 items-center justify-center",
          shape === "circle" && "overflow-hidden rounded-full",
          config.box,
          config.img,
          className,
        )}
      >
        {resolvedIcon}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "grid shrink-0 place-items-center overflow-hidden font-semibold leading-none",
        roundedClass,
        config.box,
        config.letterText,
        className,
      )}
      style={brandIconFillStyle(letterColor)}
      aria-hidden
    >
      <span className="block leading-none translate-y-[-0.06em]">
        {label.slice(0, 1).toUpperCase()}
      </span>
    </span>
  );
});

/** 兼容旧用法：返回 BrandRankIcon 节点 */
export function buildBrandRankIcon(
  label: string,
  props?: Omit<BrandRankIconProps, "label">,
): ReactNode | undefined {
  const trimmed = label.trim();
  if (!trimmed) return undefined;
  return <BrandRankIcon label={trimmed} {...props} />;
}

type BrandRankIconGroupProps = {
  labels: string[];
  maxVisible?: number;
  size?: BrandRankIconSize;
  shape?: BrandRankIconShape;
  className?: string;
  iconClassName?: string;
};

const DEFAULT_MAX_VISIBLE = 3;

/** 多品牌图标叠放；空列表显示 —，超出 maxVisible 显示 +N */
export function BrandRankIconGroup({
  labels,
  maxVisible = DEFAULT_MAX_VISIBLE,
  size = "sm",
  shape = "square",
  className,
  iconClassName,
}: BrandRankIconGroupProps) {
  if (labels.length === 0) {
    return <span className="text-muted-foreground text-sm">—</span>;
  }

  const visible = labels.slice(0, maxVisible);
  const overflow = labels.length - visible.length;

  return (
    <div className={cn("flex items-center -space-x-1", className)}>
      {visible.map((label) => (
        <BrandRankIcon
          key={label}
          label={label}
          size={size}
          shape={shape}
          className={cn("ring-2 ring-surface", iconClassName)}
        />
      ))}
      {overflow > 0 ? (
        <span className="text-muted-foreground pl-2 text-xs font-medium tabular-nums">
          +{overflow}
        </span>
      ) : null}
    </div>
  );
}
