import { useEffect, useMemo, useRef, useState } from "react";

import { resolveChartXAxisLayout } from "@/lib/analysis/chart";

type UseChartDateAxisLayoutOptions = {
  pointCount: number;
  yAxisWidth?: number;
  marginLeft?: number;
  marginRight?: number;
};

/** 监听图表容器宽度，按绘图区尺寸解析日期 X 轴标签格式与 minTickGap */
export function useChartDateAxisLayout({
  pointCount,
  yAxisWidth = 0,
  marginLeft = 0,
  marginRight = 0,
}: UseChartDateAxisLayoutOptions) {
  const plotRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const element = plotRef.current;
    if (!element) return;

    const updateWidth = () => {
      setContainerWidth(element.getBoundingClientRect().width);
    };

    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(element);
    return () => observer.disconnect();
  }, [pointCount]);

  const xAxisLayout = useMemo(() => {
    const plotWidth = Math.max(0, containerWidth - yAxisWidth - marginLeft - marginRight);
    return resolveChartXAxisLayout(plotWidth, pointCount);
  }, [containerWidth, yAxisWidth, marginLeft, marginRight, pointCount]);

  return { plotRef, xAxisLayout };
}
