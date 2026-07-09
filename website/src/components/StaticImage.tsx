import type { StaticImage as StaticImageMeta } from "@/lib/assets";

type Props = {
  /** 静态资源 URL；与 image 二选一 */
  src?: string;
  /** 来自 assets.ts 的静态图元数据；与 src 二选一 */
  image?: StaticImageMeta;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
  loading?: "eager" | "lazy";
  decoding?: "async" | "auto" | "sync";
};

export default function StaticImage({
  src,
  image,
  alt,
  width,
  height,
  className,
  loading = "lazy",
  decoding = "async",
}: Props) {
  const resolvedSrc = src ?? image?.url;
  const resolvedWidth = width ?? image?.width;
  const resolvedHeight = height ?? image?.height;

  return (
    <img
      src={resolvedSrc}
      alt={alt}
      width={resolvedWidth}
      height={resolvedHeight}
      className={className}
      loading={loading}
      decoding={decoding}
      data-image-component
    />
  );
}
