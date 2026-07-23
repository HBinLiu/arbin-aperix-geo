import { api } from "@/api/client";
import type { CompetitorItem, CompetitorsData, PromoteBrandData, SamplingPlatform, SubjectPrompt, SubjectTopic } from "@/types";

export async function fetchSamplingPlatforms(): Promise<SamplingPlatform[]> {
  const { data } = await api.get<SamplingPlatform[]>("/sampling/platforms");
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

export async function addSubjectCompetitor(
  subjectId: string,
  body: Omit<CompetitorItem, "id">,
): Promise<CompetitorItem> {
  const { data } = await api.post<CompetitorItem>(`/subjects/${subjectId}/competitors`, body, {
    skipErrorToast: true,
  });
  return data;
}

export async function deleteSubjectCompetitor(
  subjectId: string,
  competitorId: string,
): Promise<CompetitorsData> {
  const { data } = await api.delete<CompetitorsData>(
    `/subjects/${subjectId}/competitors/${competitorId}`,
    { skipErrorToast: true },
  );
  return data;
}

export async function updateSubjectCompetitor(
  subjectId: string,
  competitorId: string,
  body: Omit<CompetitorItem, "id">,
): Promise<CompetitorItem> {
  const { data } = await api.patch<CompetitorItem>(
    `/subjects/${subjectId}/competitors/${competitorId}`,
    body,
    { skipErrorToast: true },
  );
  return data;
}

export async function promoteSubjectBrand(
  subjectId: string,
  brandId: string,
): Promise<PromoteBrandData> {
  const { data } = await api.post<PromoteBrandData>(
    `/subjects/${subjectId}/brands/${brandId}/promote`,
    {},
  );
  return data;
}

export async function promotePromptFanout(
  subjectId: string,
  promptId: string,
  body: { query: string; enabled?: boolean },
): Promise<SubjectPrompt> {
  const { data } = await api.post<SubjectPrompt>(
    `/subjects/${subjectId}/prompts/${promptId}/fanout`,
    body,
    { skipErrorToast: true },
  );
  return data;
}
