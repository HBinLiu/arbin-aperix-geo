import { api } from "@/api/client";
import type { LlmResponseDetail } from "@/types";

export async function fetchLlmResponse(responseId: string): Promise<LlmResponseDetail> {
  const { data } = await api.get<LlmResponseDetail>(`/responses/${responseId}`);
  return data;
}
