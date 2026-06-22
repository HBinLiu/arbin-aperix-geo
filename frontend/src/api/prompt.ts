import { api } from "@/api/client";
import type { GeneratedPromptItem, SubjectPrompt, SubjectTopic } from "@/types";

export type PromptCreateBody = {
  topic_id: string;
  text: string;
  funnel_stage?: string;
  search_intent?: string;
  enabled?: boolean;
};

export type PromptUpdateBody = {
  topic_id?: string;
  text?: string;
  enabled?: boolean;
};

export type TopicCreateBody = {
  name: string;
};

export async function createSubjectTopic(
  subjectId: string,
  body: TopicCreateBody,
): Promise<SubjectTopic> {
  const { data } = await api.post<SubjectTopic>(`/subjects/${subjectId}/topics`, body);
  return data;
}

export async function updateSubjectTopic(
  subjectId: string,
  topicId: string,
  body: TopicCreateBody,
): Promise<SubjectTopic> {
  const { data } = await api.patch<SubjectTopic>(`/subjects/${subjectId}/topics/${topicId}`, body);
  return data;
}

export async function deleteSubjectTopic(subjectId: string, topicId: string): Promise<void> {
  await api.delete(`/subjects/${subjectId}/topics/${topicId}`);
}

export async function createSubjectPrompt(
  subjectId: string,
  body: PromptCreateBody,
): Promise<SubjectPrompt> {
  const { data } = await api.post<SubjectPrompt>(`/subjects/${subjectId}/prompts`, body);
  return data;
}

export async function updateSubjectPrompt(
  subjectId: string,
  promptId: string,
  body: PromptUpdateBody,
): Promise<SubjectPrompt> {
  const { data } = await api.patch<SubjectPrompt>(
    `/subjects/${subjectId}/prompts/${promptId}`,
    body,
  );
  return data;
}

export async function deleteSubjectPrompt(subjectId: string, promptId: string): Promise<void> {
  await api.delete(`/subjects/${subjectId}/prompts/${promptId}`);
}

export type PromptBatchCreateBody = {
  topic_id: string;
  items: Array<{
    text: string;
    funnel_stage?: string;
    search_intent?: string;
  }>;
};

export async function batchCreateSubjectPrompts(
  subjectId: string,
  body: PromptBatchCreateBody,
): Promise<SubjectPrompt[]> {
  const { data } = await api.post<SubjectPrompt[]>(`/subjects/${subjectId}/prompts/batch`, body);
  return data;
}

export type GenerateSubjectPromptsBody = {
  topic_id: string;
  count: number;
};

export async function previewSubjectPrompts(
  subjectId: string,
  body: GenerateSubjectPromptsBody,
): Promise<GeneratedPromptItem[]> {
  const { data } = await api.post<GeneratedPromptItem[]>(
    `/subjects/${subjectId}/prompts/generate/preview`,
    body,
    { timeout: 120_000 },
  );
  return data;
}
