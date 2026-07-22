import { api } from "@/api/client";
import type { SubjectKnowledgeDetail } from "@/types";

export type KnowledgeTextSourceBody = {
  text: string;
  title?: string;
};

export async function fetchSubjectKnowledge(subjectId: string): Promise<SubjectKnowledgeDetail> {
  const { data } = await api.get<SubjectKnowledgeDetail>(`/subjects/${subjectId}/knowledge`);
  return data;
}

export async function enqueueKnowledgeExtract(subjectId: string): Promise<SubjectKnowledgeDetail> {
  const { data } = await api.post<SubjectKnowledgeDetail>(`/subjects/${subjectId}/knowledge/extract`);
  return data;
}

export async function enqueueKnowledgeReindex(subjectId: string): Promise<SubjectKnowledgeDetail> {
  const { data } = await api.post<SubjectKnowledgeDetail>(`/subjects/${subjectId}/knowledge/reindex`);
  return data;
}

export async function upsertKnowledgeTextSource(
  subjectId: string,
  body: KnowledgeTextSourceBody,
): Promise<SubjectKnowledgeDetail> {
  const { data } = await api.post<SubjectKnowledgeDetail>(`/subjects/${subjectId}/knowledge/sources/text`, body);
  return data;
}

export async function uploadKnowledgeSourceFile(
  subjectId: string,
  file: File,
): Promise<SubjectKnowledgeDetail> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<SubjectKnowledgeDetail>(
    `/subjects/${subjectId}/knowledge/sources/upload`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}

export async function deleteKnowledgeSource(subjectId: string, sourceId: string): Promise<SubjectKnowledgeDetail> {
  const { data } = await api.delete<SubjectKnowledgeDetail>(
    `/subjects/${subjectId}/knowledge/sources/${sourceId}`,
  );
  return data;
}
