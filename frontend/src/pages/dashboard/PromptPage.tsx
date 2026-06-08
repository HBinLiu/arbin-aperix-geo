import { useEffect, useMemo, useState } from "react";

import {
  PromptEnabledField,
  PromptFormDialog,
  PromptTextField,
  PromptTopicField,
} from "@/components/prompt/PromptFormDialog";
import { PromptCreateDialog } from "@/components/prompt/PromptCreateDialog";
import { PromptGenerateDialog } from "@/components/prompt/PromptGenerateDialog";
import { PromptUploadDialog } from "@/components/prompt/PromptUploadDialog";
import { PromptConfirmDialog } from "@/components/prompt/PromptConfirmDialog";
import { PromptTable } from "@/components/prompt/PromptTable";
import { PromptToolbar } from "@/components/prompt/PromptToolbar";
import { PromptTopicSidebar } from "@/components/prompt/PromptTopicSidebar";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { usePromptManagement } from "@/hooks/usePromptManagement";
import {
  filterPrompts,
  PROMPT_MAX_PER_TOPIC,
  PROMPT_TOPIC_ALL,
  topicPromptRemaining,
  type PromptEnabledFilter,
  type PromptTableRow,
} from "@/lib/prompt";
import { parsePromptCsv } from "@/lib/prompt/upload";
import { toast } from "@/lib/toast";

type DialogMode =
  | { type: "add-topic" }
  | { type: "add-prompt" }
  | { type: "edit-prompt"; row: PromptTableRow };

/** 提示词管理页 */
export function PromptContent() {
  const { subject } = useDashboardContext();
  const {
    topics,
    prompts,
    isLoading,
    isMutating,
    createTopic,
    createPrompt,
    updatePrompt,
    removePrompt,
    generatePrompts,
  } = usePromptManagement(subject.id);

  const [selectedTopicId, setSelectedTopicId] = useState<string>(PROMPT_TOPIC_ALL);
  const [enabledFilter, setEnabledFilter] = useState<PromptEnabledFilter>("all");
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [dialog, setDialog] = useState<DialogMode | null>(null);
  const [topicName, setTopicName] = useState("");
  const [promptText, setPromptText] = useState("");
  const [promptTopicId, setPromptTopicId] = useState("");
  const [promptEnabled, setPromptEnabled] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [generateTopicId, setGenerateTopicId] = useState("");
  const [generateCount, setGenerateCount] = useState(1);
  const [toggleConfirmRow, setToggleConfirmRow] = useState<PromptTableRow | null>(null);

  useEffect(() => {
    setSelectedTopicId(PROMPT_TOPIC_ALL);
    setEnabledFilter("all");
    setSearch("");
    setSelectedIds(new Set());
  }, [subject.id]);

  useEffect(() => {
    if (!promptTopicId && topics[0]?.id) {
      setPromptTopicId(topics[0].id);
    }
  }, [topics, promptTopicId]);

  const filteredPrompts = useMemo(
    () =>
      filterPrompts(prompts, {
        topicId: selectedTopicId,
        enabledFilter,
        search,
      }),
    [prompts, selectedTopicId, enabledFilter, search],
  );

  const topicOptions = useMemo(
    () => topics.map((topic) => ({ value: topic.id, label: topic.name })),
    [topics],
  );

  const generateRemaining = useMemo(
    () => (generateTopicId ? topicPromptRemaining(generateTopicId, prompts) : 0),
    [generateTopicId, prompts],
  );

  useEffect(() => {
    if (!generateOpen || !generateTopicId) return;
    setGenerateCount((prev) => {
      if (generateRemaining <= 0) return 0;
      return Math.min(Math.max(prev, 1), generateRemaining);
    });
  }, [generateOpen, generateTopicId, generateRemaining]);

  const openAddTopic = () => {
    setTopicName("");
    setDialog({ type: "add-topic" });
  };

  const openAddPrompt = () => {
    if (topics.length === 0) {
      toast.error("请先添加主题。");
      return;
    }
    setPromptText("");
    setPromptTopicId(
      selectedTopicId === PROMPT_TOPIC_ALL ? (topics[0]?.id ?? "") : selectedTopicId,
    );
    setDialog({ type: "add-prompt" });
  };

  const openEditPrompt = (row: PromptTableRow) => {
    setPromptText(row.text);
    setPromptTopicId(row.topicId);
    setPromptEnabled(row.enabled);
    setDialog({ type: "edit-prompt", row });
  };

  const closeDialog = () => {
    if (!isMutating) setDialog(null);
  };

  const handleSubmitDialog = async () => {
    if (!dialog) return;

    try {
      if (dialog.type === "add-topic") {
        const name = topicName.trim();
        if (!name) {
          toast.error("请填写主题名称。");
          return;
        }
        await createTopic.mutateAsync({ name });
        toast.success("主题已添加。");
      }

      if (dialog.type === "add-prompt") {
        return;
      }

      if (dialog.type === "edit-prompt") {
        const text = promptText.trim();
        if (!text) {
          toast.error("请填写提示词内容。");
          return;
        }
        await updatePrompt.mutateAsync({
          promptId: dialog.row.id,
          body: {
            text,
            topic_id: promptTopicId,
            enabled: promptEnabled,
          },
        });
        toast.success("提示词已更新。");
      }

      setDialog(null);
    } catch {
      // API 层已处理 toast
    }
  };

  const handleDeletePrompt = async (row: PromptTableRow) => {
    if (!window.confirm(`确定删除提示词「${row.text.length > 24 ? `${row.text.slice(0, 24)}…` : row.text}」吗？`)) return;
    try {
      await removePrompt.mutateAsync(row.id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(row.id);
        return next;
      });
      toast.success("提示词已删除。");
    } catch {
      // handled by API
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`确定删除选中的 ${selectedIds.size} 条提示词吗？`)) return;
    try {
      await Promise.all([...selectedIds].map((id) => removePrompt.mutateAsync(id)));
      toast.success(`已删除 ${selectedIds.size} 条提示词。`);
      setSelectedIds(new Set());
    } catch {
      // handled by API
    }
  };

  const handleCreatePrompt = async () => {
    const text = promptText.trim();
    if (!text) {
      toast.error("请填写提示词。");
      return;
    }
    if (!promptTopicId) {
      toast.error("请选择主题。");
      return;
    }
    if (topicPromptRemaining(promptTopicId, prompts) <= 0) {
      toast.error(`每个主题最多可创建 ${PROMPT_MAX_PER_TOPIC} 个提示词。`);
      return;
    }

    try {
      await createPrompt.mutateAsync({
        topic_id: promptTopicId,
        text,
        enabled: true,
      });
      toast.success("提示词已创建。");
      setDialog(null);
    } catch {
      // handled by API
    }
  };

  const openGenerate = () => {
    if (topics.length === 0) {
      toast.error("请先添加主题。");
      return;
    }
    const topicId =
      selectedTopicId === PROMPT_TOPIC_ALL ? (topics[0]?.id ?? "") : selectedTopicId;
    const remaining = topicPromptRemaining(topicId, prompts);
    setGenerateTopicId(topicId);
    setGenerateCount(remaining > 0 ? Math.min(9, remaining) : 0);
    setGenerateOpen(true);
  };

  const handleGenerateSubmit = async () => {
    if (!generateTopicId || generateCount <= 0) return;
    try {
      const created = await generatePrompts.mutateAsync({
        topic_id: generateTopicId,
        count: generateCount,
      });
      toast.success(`成功生成 ${created.length} 条提示词。`);
      setGenerateOpen(false);
    } catch {
      // handled by API
    }
  };

  const handleUploadImport = async () => {
    if (!uploadFile) return;

    const content = await uploadFile.text();
    const { rows, errors } = parsePromptCsv(content);
    if (errors.length > 0) {
      toast.error(errors[0]);
      return;
    }

    setUploading(true);
    try {
      const topicByName = new Map(topics.map((topic) => [topic.name.toLowerCase(), topic.id]));
      let created = 0;
      let skipped = 0;

      for (const row of rows) {
        let topicId = topicByName.get(row.topic.toLowerCase());
        if (!topicId) {
          const topic = await createTopic.mutateAsync({ name: row.topic });
          topicId = topic.id;
          topicByName.set(row.topic.toLowerCase(), topicId);
        }

        try {
          await createPrompt.mutateAsync({
            topic_id: topicId,
            text: row.prompt,
            enabled: true,
          });
          created += 1;
        } catch {
          skipped += 1;
        }
      }

      const suffix = skipped > 0 ? `，跳过 ${skipped} 条` : "";
      toast.success(`成功导入 ${created} 条提示词${suffix}。`);
      setUploadOpen(false);
      setUploadFile(null);
    } catch {
      // handled by API
    } finally {
      setUploading(false);
    }
  };

  const handleToggleEnabled = (row: PromptTableRow) => {
    setToggleConfirmRow(row);
  };

  const handleConfirmToggleEnabled = async () => {
    if (!toggleConfirmRow) return;
    const nextEnabled = !toggleConfirmRow.enabled;
    try {
      await updatePrompt.mutateAsync({
        promptId: toggleConfirmRow.id,
        body: { enabled: nextEnabled },
      });
      toast.success(nextEnabled ? "提示词已启用。" : "提示词已停用。");
      setToggleConfirmRow(null);
    } catch {
      // handled by API
    }
  };

  return (
    <div className="flex min-h-0 min-w-0 w-full flex-1 flex-row overflow-hidden">
      <PromptTopicSidebar
        topics={topics}
        prompts={prompts}
        selectedTopicId={selectedTopicId}
        onSelectTopic={setSelectedTopicId}
        onAddTopic={openAddTopic}
        loading={isLoading}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
        <PromptToolbar
          enabledFilter={enabledFilter}
          onEnabledFilterChange={setEnabledFilter}
          search={search}
          onSearchChange={setSearch}
          selectedCount={selectedIds.size}
          onBatchDelete={handleBatchDelete}
          onUpload={() => {
            setUploadFile(null);
            setUploadOpen(true);
          }}
          onGenerate={openGenerate}
          onAddPrompt={openAddPrompt}
          disabled={isLoading || isMutating || uploading}
        />

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <PromptTable
            rows={filteredPrompts}
            topics={topics}
            selectedIds={selectedIds}
            onSelectedIdsChange={setSelectedIds}
            onEdit={openEditPrompt}
            onDelete={handleDeletePrompt}
            onToggleEnabled={handleToggleEnabled}
            loading={isLoading}
          />
        </div>
      </div>

      <PromptGenerateDialog
        open={generateOpen}
        topicId={generateTopicId}
        onTopicIdChange={setGenerateTopicId}
        topicOptions={topicOptions}
        count={generateCount}
        onCountChange={setGenerateCount}
        remaining={generateRemaining}
        submitting={generatePrompts.isPending}
        onOpenChange={(open) => !open && !generatePrompts.isPending && setGenerateOpen(false)}
        onSubmit={() => void handleGenerateSubmit()}
      />

      <PromptUploadDialog
        open={uploadOpen}
        file={uploadFile}
        onFileChange={setUploadFile}
        submitting={uploading}
        onOpenChange={(open) => {
          if (!open && !uploading) {
            setUploadOpen(false);
            setUploadFile(null);
          }
        }}
        onImport={() => void handleUploadImport()}
      />

      <PromptConfirmDialog
        open={toggleConfirmRow !== null}
        title="更新提示词状态"
        description="确定要更改此提示词的状态吗？"
        submitting={updatePrompt.isPending}
        onOpenChange={(open) => !open && setToggleConfirmRow(null)}
        onConfirm={() => void handleConfirmToggleEnabled()}
      />

      <PromptFormDialog
        open={dialog?.type === "add-topic"}
        title="添加主题"
        submitLabel="添加主题"
        submitting={createTopic.isPending}
        onOpenChange={(open) => !open && closeDialog()}
        onSubmit={() => void handleSubmitDialog()}
      >
        <PromptTextField
          id="topic-name"
          label="主题名称"
          value={topicName}
          onChange={setTopicName}
          placeholder="请输入主题名称"
        />
      </PromptFormDialog>

      <PromptCreateDialog
        open={dialog?.type === "add-prompt"}
        topicId={promptTopicId}
        onTopicIdChange={setPromptTopicId}
        topicOptions={topicOptions}
        text={promptText}
        onTextChange={setPromptText}
        submitting={createPrompt.isPending}
        onOpenChange={(open) => !open && closeDialog()}
        onSubmit={() => void handleCreatePrompt()}
      />

      <PromptFormDialog
        open={dialog?.type === "edit-prompt"}
        title="编辑提示词"
        submitLabel="保存"
        submitting={updatePrompt.isPending}
        onOpenChange={(open) => !open && closeDialog()}
        onSubmit={() => void handleSubmitDialog()}
      >
        <PromptTextField
          id="edit-prompt-text"
          label="提示词"
          value={promptText}
          onChange={setPromptText}
          multiline
        />
        <PromptTopicField
          id="edit-prompt-topic"
          label="主题"
          value={promptTopicId}
          onChange={setPromptTopicId}
          options={topicOptions}
        />
        <PromptEnabledField enabled={promptEnabled} onChange={setPromptEnabled} />
      </PromptFormDialog>
    </div>
  );
}
