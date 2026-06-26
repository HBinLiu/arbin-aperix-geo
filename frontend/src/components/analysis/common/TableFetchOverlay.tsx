import { Loader2 } from "lucide-react";

/** 表格内容区加载遮罩：翻页/排序时覆盖在已有数据上方 */
export function TableFetchOverlay() {
  return (
    <div
      className="absolute inset-0 z-20 flex items-center justify-center bg-muted-background/75 backdrop-blur-[2px]"
      role="status"
      aria-label="加载中"
    >
      <Loader2 className="text-primary size-7 animate-spin" aria-hidden />
    </div>
  );
}
