import { useCallback, useEffect, useMemo, useState } from "react";

import {
  resolveVisibilityChartMode,
  visibilityChartLabels,
  type VisibilityChartMode,
} from "@/lib/analysis/visibility";

/** 可见度页图表 UI 状态（纯前端，不触发数据请求） */
export function useVisibilityChartUI(topLabels: string[], ownLabel: string, scopeKey: string) {
  const [showCompare, setShowCompare] = useState(true);
  const [showCurrentPeriod, setShowCurrentPeriod] = useState(true);
  const [showPreviousPeriod, setShowPreviousPeriod] = useState(false);
  const [hiddenLegendKeys, setHiddenLegendKeys] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setHiddenLegendKeys(new Set());
  }, [scopeKey]);

  const chartMode: VisibilityChartMode = useMemo(
    () => resolveVisibilityChartMode(showCompare, showPreviousPeriod),
    [showCompare, showPreviousPeriod],
  );

  const chartLabels = useMemo(
    () => visibilityChartLabels(chartMode, topLabels, ownLabel),
    [chartMode, topLabels, ownLabel],
  );

  const toggleLegendKey = useCallback((key: string) => {
    setHiddenLegendKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const handleToggleCompare = useCallback((checked: boolean) => {
    setShowCompare(checked);
    if (checked) {
      setShowPreviousPeriod(false);
    } else {
      setHiddenLegendKeys(new Set());
      setShowPreviousPeriod(true);
    }
  }, []);

  return {
    showCompare,
    showCurrentPeriod,
    showPreviousPeriod,
    chartMode,
    chartLabels,
    hiddenLegendKeys,
    setShowCurrentPeriod,
    setShowPreviousPeriod,
    toggleLegendKey,
    handleToggleCompare,
  };
}
