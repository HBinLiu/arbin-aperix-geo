import { api } from "@/api/client";
import type { CompetitorsData, SamplingPlatform, SubjectPrompt, SubjectTopic } from "@/types";

export async function fetchSamplingPlatforms(): Promise<SamplingPlatform[]> {
  const { data } = await api.get<SamplingPlatform[]>("/sampling-platforms");
  return data;
}

export async function fetchSubjectTopics(subjectId: string): Promise<SubjectTopic[]> {
  const { data } = await api.get<SubjectTopic[]>(`/subjects/${subjectId}/topics`);
  return data;
}

export async function fetchSubjectPrompts(subjectId: string): Promise<SubjectPrompt[]> {
  const { data } = await api.get<SubjectPrompt[]>(`/subjects/${subjectId}/prompts`);
  return data;
}

export async function fetchSubjectCompetitors(subjectId: string): Promise<CompetitorsData> {
  const { data } = await api.get<CompetitorsData>(`/subjects/${subjectId}/competitors`);
  return data;
}

export async function saveSubjectCompetitors(
  subjectId: string,
  body: Pick<CompetitorsData, "competitors">,
): Promise<CompetitorsData> {
  const { data } = await api.put<CompetitorsData>(`/subjects/${subjectId}/competitors`, body, {
    skipErrorToast: true,
  });
  return data;
}
