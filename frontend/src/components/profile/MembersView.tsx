import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Trash2 } from "lucide-react";

import { removeTenantMember, fetchTenantMembers } from "@/api/members";
import { formatApiError } from "@/api/client";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { InviteMemberDialog } from "@/components/profile/InviteMemberDialog";
import { PromptConfirmDialog } from "@/components/prompt/PromptConfirmDialog";
import { Button } from "@/components/ui/button";
import { DotBadge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useTenantSubscription } from "@/hooks/useTenantSubscription";
import { isAtTeamMemberLimit, maxTeamMembers } from "@/lib/billing/limits";
import { formatPromptCreatedAt } from "@/lib/prompt";
import { queryKeys } from "@/lib/queries";
import { toast } from "@/lib/toast";
import type { TenantMember, TenantMemberRole } from "@/types/members";

const MEMBER_TABLE_MIN_WIDTH = 640;

const MEMBER_TABLE_COLUMNS = [
  { id: "phone", width: "25%" },
  { id: "role", width: "18%" },
  { id: "status", width: "16%" },
  { id: "joinedAt", width: "25%" },
  { id: "actions", width: "16%" },
] as const;

const ROLE_LABELS: Record<TenantMemberRole, string> = {
  admin: "管理员",
  member: "成员",
  readonly: "只读",
};

function MembersTableSkeleton() {
  return (
    <>
      {Array.from({ length: 3 }).map((_, index) => (
        <tr key={index} className={performanceTableClasses.row} aria-hidden>
          {Array.from({ length: 5 }).map((__, col) => (
            <td key={col}>
              <Skeleton className="h-4 w-full max-w-[8rem]" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

/** 账户设置 · 团队成员 */
export function MembersView() {
  const queryClient = useQueryClient();
  const { user } = useDashboardContext();
  const isAdmin = user.role === "admin";
  const [query, setQuery] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<TenantMember | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.tenantMembers,
    queryFn: fetchTenantMembers,
  });

  const { data: subscription } = useTenantSubscription();

  const rows = useMemo(() => data?.items ?? [], [data]);
  const maxMembers = maxTeamMembers(subscription);
  const atMemberLimit = isAtTeamMemberLimit(subscription, rows.length);

  const filtered = useMemo(() => {
    const q = query.trim();
    if (!q) return rows;
    return rows.filter((row) => row.phone.includes(q));
  }, [rows, query]);

  const removeMutation = useMutation({
    mutationFn: removeTenantMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tenantMembers });
      setRemoveTarget(null);
      toast.success("成员已移除");
    },
    onError: (error: unknown) => {
      toast.error(formatApiError(error, "移除成员失败。"));
    },
  });

  return (
    <>
      <div className="flex flex-col gap-3 px-2 py-6 sm:px-3 md:px-4 lg:px-6 xl:px-8">
        <div className="flex flex-wrap items-center gap-2 gap-y-3">
          <div className="relative w-full max-w-xs sm:w-[240px]">
            <Search
              className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2"
              aria-hidden
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索手机号…"
              className="pl-9"
            />
          </div>
          {isAdmin ? (
            <div className="ml-auto flex items-center gap-3">
              <p className="text-muted-foreground whitespace-nowrap text-xs sm:text-sm">
                已添加 {rows.length}/{maxMembers} 人
              </p>
              <Button
                type="button"
                variant="default"
                size="sm"
                className="gap-1.5"
                disabled={atMemberLimit}
                onClick={() => setInviteOpen(true)}
              >
                <Plus className="size-4" aria-hidden />
                邀请成员
              </Button>
            </div>
          ) : null}
        </div>

        <PerformanceTableShell className="overflow-visible" loading={isLoading} scrollMinWidth={MEMBER_TABLE_MIN_WIDTH}>
          <table className={performanceTableClasses.topicTable}>
            <colgroup>
              {MEMBER_TABLE_COLUMNS.map((column) => (
                <col key={column.id} style={{ width: column.width }} />
              ))}
            </colgroup>
            <thead className={performanceTableClasses.head}>
              <tr>
                <th>手机号</th>
                <th>角色</th>
                <th>状态</th>
                <th>加入时间</th>
                <th className="text-center">操作</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <MembersTableSkeleton />
              ) : filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="text-muted-foreground px-2 py-10 text-center text-sm"
                  >
                    {query.trim() ? "没有匹配的成员" : "暂无成员"}
                  </td>
                </tr>
              ) : (
                filtered.map((row) => {
                  const isSelf = row.id === user.id;
                  const canRemove = isAdmin && !isSelf;
                  return (
                    <tr key={row.id} className={performanceTableClasses.row}>
                      <td>
                        <span className="font-medium tabular-nums">{row.phone}</span>
                      </td>
                      <td>
                        <span className="font-medium tabular-nums">{ROLE_LABELS[row.role] ?? row.role}</span>
                      </td>
                      <td>
                        <DotBadge
                          variant={row.is_active ? "success" : "gray"}
                          className="px-1.5 py-0.5 font-semibold"
                        >
                          {row.is_active ? "启用" : "已禁用"}
                        </DotBadge>
                      </td>
                      <td className="tabular-nums">{formatPromptCreatedAt(row.created_at)}</td>
                      <td className="text-center">
                        {canRemove ? (
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            className="text-destructive hover:text-destructive size-8 rounded-md"
                            aria-label={`移除 ${row.phone}`}
                            onClick={() => setRemoveTarget(row)}
                          >
                            <Trash2 className="size-4" aria-hidden />
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </PerformanceTableShell>
      </div>

      <InviteMemberDialog open={inviteOpen} onOpenChange={setInviteOpen} />

      <PromptConfirmDialog
        open={Boolean(removeTarget)}
        title="移除成员"
        description={
          removeTarget
            ? `确定将 ${removeTarget.phone} 移出当前工作区？该账号将无法再访问此工作区。`
            : ""
        }
        confirmLabel="移除"
        submitting={removeMutation.isPending}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
        onConfirm={() => {
          if (removeTarget) {
            removeMutation.mutate(removeTarget.id);
          }
        }}
      />
    </>
  );
}
