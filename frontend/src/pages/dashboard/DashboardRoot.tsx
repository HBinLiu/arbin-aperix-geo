import { useCallback, useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AppShellError, AppShellLoading } from "@/components/common/AppShellState";
import { fetchMe } from "@/api/auth";
import { fetchSubjects } from "@/api/subject";
import { DashboardProvider } from "@/hooks/useDashboardContext";
import {
  getStoredActiveSubjectId,
  resolveActiveSubject,
  setStoredActiveSubjectId,
} from "@/lib/subject";
import { DASHBOARD_SETUP_PATH } from "@/lib/dashboard";
import { queryKeys } from "@/lib/queries";

const QUERY_RETRY = { retry: 1 } as const;

/** 控制台布局门控：无 subject 时跳转 setup，否则注入 DashboardProvider。 */
export function DashboardRoot() {
  const navigate = useNavigate();
  const [activeSubjectId, setActiveSubjectIdState] = useState(getStoredActiveSubjectId);

  const setActiveSubjectId = useCallback((id: string) => {
    setStoredActiveSubjectId(id);
    setActiveSubjectIdState(id);
  }, []);

  const subjectsQuery = useQuery({
    queryKey: queryKeys.subjects,
    queryFn: fetchSubjects,
    ...QUERY_RETRY,
    retryDelay: 800,
  });

  const subjects = subjectsQuery.data ?? [];

  useEffect(() => {
    if (subjectsQuery.isPending || subjectsQuery.isError) return;
    if (subjects.length === 0) {
      navigate(DASHBOARD_SETUP_PATH, { replace: true });
    }
  }, [subjects.length, subjectsQuery.isPending, subjectsQuery.isError, navigate]);

  useEffect(() => {
    if (subjects.length === 0) return;
    const exists = activeSubjectId && subjects.some((s) => s.id === activeSubjectId);
    if (!exists) {
      setStoredActiveSubjectId(subjects[0].id);
      setActiveSubjectIdState(subjects[0].id);
    }
  }, [subjects, activeSubjectId]);

  const userQuery = useQuery({
    queryKey: queryKeys.me,
    queryFn: fetchMe,
    enabled: subjects.length > 0,
    ...QUERY_RETRY,
  });

  if (subjectsQuery.isPending) {
    return <AppShellLoading message="加载工作区…" />;
  }

  if (subjectsQuery.isError) {
    return (
      <AppShellError
        variant="workspace"
        title="工作区加载失败"
        error={subjectsQuery.error}
        retrying={subjectsQuery.isFetching}
        onRetry={() => void subjectsQuery.refetch()}
      />
    );
  }

  if (subjects.length === 0) {
    return <AppShellLoading message="加载工作区…" />;
  }

  if (userQuery.isPending) {
    return <AppShellLoading message="加载用户信息…" />;
  }

  if (userQuery.isError || !userQuery.data) {
    return (
      <AppShellError
        variant="profile"
        title="用户信息加载失败"
        error={userQuery.error}
        retrying={userQuery.isFetching}
        onRetry={() => void userQuery.refetch()}
      />
    );
  }

  const subject = resolveActiveSubject(subjects, activeSubjectId);
  if (!subject) {
    return <AppShellLoading message="加载工作区…" />;
  }

  return (
    <DashboardProvider
      subject={subject}
      subjects={subjects}
      user={userQuery.data}
      setActiveSubjectId={setActiveSubjectId}
    >
      <Outlet />
    </DashboardProvider>
  );
}
