import { useEffect, useState } from "react";

const SIDEBAR_AUTO_COLLAPSE_QUERY = "(max-width: 1024px)";

export function useDashboardSidebar() {
  const [isNarrow, setIsNarrow] = useState(
    () => typeof window !== "undefined" && window.matchMedia(SIDEBAR_AUTO_COLLAPSE_QUERY).matches,
  );
  const [userOverride, setUserOverride] = useState<boolean | null>(null);

  useEffect(() => {
    const mq = window.matchMedia(SIDEBAR_AUTO_COLLAPSE_QUERY);
    const onChange = () => {
      setIsNarrow(mq.matches);
      setUserOverride(null);
    };
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const collapsed = userOverride ?? isNarrow;
  const toggle = () => setUserOverride(!collapsed);

  return { collapsed, toggle };
}
