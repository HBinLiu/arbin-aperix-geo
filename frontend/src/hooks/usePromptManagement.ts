import { useMutation, useQuery } from "@tanstack/react-query";

import { fetchSubjectPrompts, fetchSubjectTopics } from "@/api/brand";
import {
  batchCreateSubjectPrompts,
  createSubjectPrompt,
  createSubjectTopic,
  deleteSubjectPrompt,
  deleteSubjectTopic,
  previewSubjectPrompts,
  updateSubjectPrompt,
  updateSubjectTopic,
  type GenerateSubjectPromptsBody,
  type PromptBatchCreateBody,
  type PromptCreateBody,
  type PromptUpdateBody,
  type TopicCreateBody,
} from "@/api/prompt";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";

export function usePromptManagement(subjectId: string) {
  const topicsQuery = useQuery({
    queryKey: queryKeys.subjectTopics(subjectId),
    queryFn: () => fetchSubjectTopics(subjectId),
    ...sessionCatalogQueryOptions,
  });

  const promptsQuery = useQuery({
    queryKey: queryKeys.subjectPrompts(subjectId),
    queryFn: () => fetchSubjectPrompts(subjectId),
  });

  const refresh = async () => {
    await Promise.all([topicsQuery.refetch(), promptsQuery.refetch()]);
  };

  const createTopic = useMutation({
    mutationFn: (body: TopicCreateBody) => createSubjectTopic(subjectId, body),
    onSuccess: refresh,
  });

  const updateTopic = useMutation({
    mutationFn: ({ topicId, body }: { topicId: string; body: TopicCreateBody }) =>
      updateSubjectTopic(subjectId, topicId, body),
    onSuccess: refresh,
  });

  const removeTopic = useMutation({
    mutationFn: (topicId: string) => deleteSubjectTopic(subjectId, topicId),
    onSuccess: refresh,
  });

  const createPrompt = useMutation({
    mutationFn: (body: PromptCreateBody) => createSubjectPrompt(subjectId, body),
    onSuccess: refresh,
  });

  const updatePrompt = useMutation({
    mutationFn: ({ promptId, body }: { promptId: string; body: PromptUpdateBody }) =>
      updateSubjectPrompt(subjectId, promptId, body),
    onSuccess: refresh,
  });

  const removePrompt = useMutation({
    mutationFn: (promptId: string) => deleteSubjectPrompt(subjectId, promptId),
    onSuccess: refresh,
  });

  const previewPrompts = useMutation({
    mutationFn: (body: GenerateSubjectPromptsBody) => previewSubjectPrompts(subjectId, body),
  });

  const batchCreatePrompts = useMutation({
    mutationFn: (body: PromptBatchCreateBody) => batchCreateSubjectPrompts(subjectId, body),
    onSuccess: refresh,
  });

  const isMutating =
    createTopic.isPending ||
    updateTopic.isPending ||
    removeTopic.isPending ||
    createPrompt.isPending ||
    updatePrompt.isPending ||
    removePrompt.isPending ||
    previewPrompts.isPending ||
    batchCreatePrompts.isPending;

  return {
    topics: topicsQuery.data ?? [],
    prompts: promptsQuery.data ?? [],
    isLoading: topicsQuery.isLoading || promptsQuery.isLoading,
    isMutating,
    createTopic,
    updateTopic,
    removeTopic,
    createPrompt,
    updatePrompt,
    removePrompt,
    previewPrompts,
    batchCreatePrompts,
    refresh,
  };
}
