import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  KnowledgeStatusBar,
  KnowledgeStatusBarSkeleton,
} from "@/components/knowledge/KnowledgePanels";
import { KnowledgeSourcesSection } from "@/components/knowledge/KnowledgeSourcesSection";
import { formatApiError } from "@/api/client";
import {
  deleteKnowledgeSource,
  fetchSubjectKnowledge,
  uploadKnowledgeSourceFile,
  upsertKnowledgeTextSource,
} from "@/api/knowledge";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useSubjectKnowledge } from "@/hooks/useSubjectKnowledge";
import { DASHBOARD_SETUP_PATH } from "@/lib/dashboard";
import { MAX_SETUP_UPLOAD_FILES } from "@/lib/setup";
import { queryKeys } from "@/lib/queries";
import { toast } from "@/lib/toast";

function KnowledgeEmptyHint({ isBrand }: { isBrand: boolean }) {
  if (!isBrand) {
    return (
      <p className="text-muted-foreground text-sm leading-relaxed">
        知识库目前面向品牌模式主体。域名模式主体可在 Setup 中切换为品牌模式后建立知识库。
      </p>
    );
  }
  return (
    <p className="text-muted-foreground text-sm leading-relaxed">
      可在下方上传文件或添加手动内容建立知识库；也可
      {" "}
      <Link to={DASHBOARD_SETUP_PATH} className="text-primary hover:underline">
        前往 Setup
      </Link>
      {" "}
      完成初始化。
    </p>
  );
}

/** 知识库页：数据来源管理。 */
export function KnowledgeContent() {
  const { subject } = useDashboardContext();
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useSubjectKnowledge(subject.id);
  const isBrand = subject.type === "brand";
  const knowledge = data?.knowledge ?? null;
  const sources = data?.sources ?? [];

  const indexing = knowledge?.index_status === "indexing" || knowledge?.index_status === "pending";
  const readOnly = indexing;

  const invalidateKnowledge = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.subjectKnowledge(subject.id) });
  };

  const saveManualMutation = useMutation({
    mutationFn: (input: { title: string; text: string }) =>
      upsertKnowledgeTextSource(subject.id, input),
    onSuccess: async () => {
      toast.success("手动内容已保存");
      await invalidateKnowledge();
    },
    onError: (error) => toast.error(formatApiError(error)),
  });

  const uploadMutation = useMutation({
    mutationFn: async (files: FileList | null) => {
      if (!files?.length) return;
      const remaining = MAX_SETUP_UPLOAD_FILES - sources.filter((source) => source.kind === "upload").length;
      const batch = Array.from(files).slice(0, Math.max(remaining, 0));
      if (batch.length === 0) {
        throw new Error(`最多上传 ${MAX_SETUP_UPLOAD_FILES} 个文件。`);
      }
      let latest = await fetchSubjectKnowledge(subject.id);
      for (const file of batch) {
        latest = await uploadKnowledgeSourceFile(subject.id, file);
      }
      return latest;
    },
    onSuccess: async (result) => {
      if (!result) return;
      toast.success("文件已上传");
      await invalidateKnowledge();
    },
    onError: (error) => toast.error(formatApiError(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: (sourceId: string) => deleteKnowledgeSource(subject.id, sourceId),
    onSuccess: async () => {
      toast.success("资料已删除");
      await invalidateKnowledge();
    },
    onError: (error) => toast.error(formatApiError(error)),
  });

  const mutating =
    saveManualMutation.isPending || uploadMutation.isPending || deleteMutation.isPending;

  if (!isBrand) {
    return (
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-muted-background">
        <div className="border-border shrink-0 border-b bg-muted-background px-4 py-4 sm:px-6">
          <h1 className="text-foreground text-lg font-semibold">知识库</h1>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6">
          <div className="mx-auto w-full max-w-5xl">
            <KnowledgeEmptyHint isBrand={false} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-muted-background">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-4">
          {isError ? (
            <div className="border-border rounded-lg border bg-muted-background p-6 text-sm">
              <p className="text-destructive">知识库加载失败，请稍后重试。</p>
            </div>
          ) : (
            <>
              {!isLoading && !knowledge && sources.length === 0 ? (
                <div className="border-border rounded-lg border bg-muted-background p-4">
                  <KnowledgeEmptyHint isBrand={isBrand} />
                </div>
              ) : null}

              {isLoading ? (
                <KnowledgeStatusBarSkeleton />
              ) : knowledge ? (
                <KnowledgeStatusBar knowledge={knowledge} chunkCount={data?.chunk_count ?? 0} />
              ) : null}

              <KnowledgeSourcesSection
                loading={isLoading}
                sources={sources}
                knowledge={knowledge}
                disabled={readOnly || mutating}
                uploading={uploadMutation.isPending}
                deletingSourceId={deleteMutation.isPending ? deleteMutation.variables ?? null : null}
                savingManualText={saveManualMutation.isPending}
                onUploadFiles={(files) => uploadMutation.mutate(files)}
                onDeleteSource={(sourceId) => deleteMutation.mutate(sourceId)}
                onSaveManualText={(input) => saveManualMutation.mutateAsync(input)}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
