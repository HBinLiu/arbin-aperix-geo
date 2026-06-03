import { createContext, useContext, type ReactNode } from "react";

import type { Subject, User } from "@/types";

type DashboardContextValue = {
  subject: Subject;
  subjects: Subject[];
  user: User;
  setActiveSubjectId: (id: string) => void;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

type DashboardProviderProps = {
  subject: Subject;
  subjects: Subject[];
  user: User;
  setActiveSubjectId: (id: string) => void;
  children: ReactNode;
};

export function DashboardProvider({
  subject,
  subjects,
  user,
  setActiveSubjectId,
  children,
}: DashboardProviderProps) {
  return (
    <DashboardContext.Provider value={{ subject, subjects, user, setActiveSubjectId }}>
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboardContext(): DashboardContextValue {
  const value = useContext(DashboardContext);
  if (!value) {
    throw new Error("useDashboardContext must be used within DashboardProvider");
  }
  return value;
}
