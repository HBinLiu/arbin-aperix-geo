import { api } from "@/api/client";
import type { SubjectPrompt, SubjectTopic } from "@/types";

export type PromptCreateBody = {
  topic_id: string;
  text: string;
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

export type GenerateSubjectPromptsBody = {
  topic_id: string;
  count: number;
};

export async function generateSubjectPrompts(
  subjectId: string,
  body: GenerateSubjectPromptsBody,
): Promise<SubjectPrompt[]> {
  const { data } = await api.post<SubjectPrompt[]>(
    `/subjects/${subjectId}/prompts/generate`,
    body,
    { timeout: 120_000 },
  );
  return data;
}
