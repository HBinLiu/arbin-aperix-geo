import {
  createContext,
  useContext,
  useEffect,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";

import { useDashboardContext } from "@/hooks/useDashboardContext";
import { DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis/filters";
import type { AnalysisFilters } from "@/types";

type AnalysisFiltersContextValue = {
  filters: AnalysisFilters;
  setFilters: Dispatch<SetStateAction<AnalysisFilters>>;
};

const AnalysisFiltersContext = createContext<AnalysisFiltersContextValue | null>(null);

/** 控制台内共享筛选条件（切换页面/分析维度时保持，切换主体时重置）。 */
export function AnalysisFiltersProvider({ children }: { children: ReactNode }) {
  const { subject } = useDashboardContext();
  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);

  useEffect(() => {
    setFilters(DEFAULT_ANALYSIS_FILTERS);
  }, [subject.id]);

  return (
    <AnalysisFiltersContext.Provider value={{ filters, setFilters }}>
      {children}
    </AnalysisFiltersContext.Provider>
  );
}

export function useAnalysisFiltersState(): AnalysisFiltersContextValue {
  const value = useContext(AnalysisFiltersContext);
  if (!value) {
    throw new Error("useAnalysisFiltersState must be used within AnalysisFiltersProvider");
  }
  return value;
}
