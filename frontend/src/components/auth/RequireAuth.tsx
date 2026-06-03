import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { getStoredToken } from "@/api/client";
import { sanitizeReturnPath } from "@/lib/auth";

type Props = { children: ReactNode };

export function RequireAuth({ children }: Props) {
  const location = useLocation();
  if (!getStoredToken()) {
    const next = `${location.pathname}${location.search}`;
    const safe = sanitizeReturnPath(next);
    return <Navigate to={`/auth/login?next=${encodeURIComponent(safe)}`} replace />;
  }
  return <>{children}</>;
}
