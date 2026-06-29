import { api } from "@/api/client";
import type { Subject } from "@/types";

export type SubjectUpdatePayload = {
  brand?: string;
  aliases?: string[];
  profile_summary?: string;
  sampling_platforms?: string[];
  sampling_frequency?: string;
};

export async function fetchSubjects(): Promise<Subject[]> {
  const { data } = await api.get<Subject[]>("/subjects");
  return data;
}

export async function patchSubject(subjectId: string, body: SubjectUpdatePayload): Promise<Subject> {
  const { data } = await api.patch<Subject>(`/subjects/${subjectId}`, body, { skipErrorToast: true });
  return data;
}
