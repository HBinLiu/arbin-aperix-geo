import {
  api,
  GENERATE_PROMPTS_TIMEOUT_MS,
  SETUP_TOPICS_TIMEOUT_MS,
} from "@/api/client";
import { coalesceWebsiteUrl, registrableDomain } from "@/lib/domain";
import {
  buildFinalizePayload,
  promptRowsFromGenerated,
  rowsToPersist,
  topicRowsFromSetupTopics,
} from "@/lib/setup";
import type {
  CompetitorRow,
  FinalizeSetupInput,
  GeneratedPromptItem,
  PromptRow,
  SetupUploadFile,
  SubjectMode,
  TopicRow,
} from "@/types";

export async function createBrandSetupSession(input: {
  brand: string;
  region: string;
  language: string;
  sessionId?: string;
}): Promise<{ sessionId: string }> {
  const { data } = await api.post<{ session_id: string }>("/subjects/setup/session", {
    brand: input.brand.trim(),
    region: input.region,
    language: input.language,
    ...(input.sessionId?.trim() ? { session_id: input.sessionId.trim() } : {}),
  });
  return { sessionId: data.session_id };
}

export async function saveSetupMaterials(input: {
  sessionId: string;
  brandIntro: string;
  brandWebsiteUrl?: string;
}): Promise<void> {
  await api.put("/subjects/setup/materials", {
    session_id: input.sessionId.trim(),
    brand_intro: input.brandIntro,
    website_url: coalesceWebsiteUrl(
      input.brandWebsiteUrl ?? "",
      registrableDomain(input.brandWebsiteUrl ?? ""),
    ),
  });
}

export async function uploadSetupMaterialFile(input: {
  sessionId: string;
  file: File;
}): Promise<SetupUploadFile> {
  const form = new FormData();
  form.append("session_id", input.sessionId.trim());
  form.append("file", input.file);
  const { data } = await api.post<{ id: string; name: string; mime: string; size: number; status: string }>(
    "/subjects/setup/materials/files",
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return {
    id: data.id,
    name: data.name,
    mime: data.mime,
    size: data.size,
    status: data.status,
  };
}

export async function deleteSetupMaterialFile(input: {
  sessionId: string;
  fileId: string;
}): Promise<void> {
  await api.delete(`/subjects/setup/materials/files/${encodeURIComponent(input.fileId)}`, {
    params: { session_id: input.sessionId.trim() },
  });
}

export type DiscoverSetupResult = {
  sessionId: string;
};

/** UI Step：入队后台画像；竞品手填；主题在 topics 步带出 */
export async function discoverSetup(input: {
  mode: SubjectMode;
  domain: string;
  brand: string;
  region: string;
  language: string;
  sessionId?: string;
}): Promise<DiscoverSetupResult> {
  const domain = input.domain.trim();
  const brand = input.brand.trim();
  const sessionId = input.sessionId?.trim();
  const { data } = await api.post<{
    session_id: string;
    status?: string;
  }>("/subjects/setup/discover", {
    type: input.mode,
    ...(domain ? { domain } : {}),
    ...(brand ? { brand } : {}),
    region: input.region,
    language: input.language,
    ...(sessionId ? { session_id: sessionId } : {}),
  });
  return { sessionId: data.session_id };
}

/** UI Step：确认竞品后生成监测主题（后端可能短等画像就绪） */
export async function generateSetupTopics(input: {
  sessionId: string;
  mode: SubjectMode;
  competitorRows: CompetitorRow[];
}): Promise<{ topicRows: TopicRow[] }> {
  const { competitors } = rowsToPersist(input.mode, input.competitorRows);
  const { data } = await api.post<{
    topics: { name: string }[];
  }>(
    "/subjects/setup/topics",
    {
      session_id: input.sessionId.trim(),
      competitors,
    },
    { timeout: SETUP_TOPICS_TIMEOUT_MS },
  );
  return {
    topicRows: topicRowsFromSetupTopics(data.topics ?? []),
  };
}

/** UI Step 2→3：确认主题并生成提示词 */
export async function generateSetupPrompts(input: {
  sessionId: string;
  topics: TopicRow[];
  excludePrompts?: string[];
}): Promise<PromptRow[]> {
  const { data } = await api.post<{ items: { topic: string; prompts: GeneratedPromptItem[] }[] }>(
    "/subjects/setup/prompts",
    {
      session_id: input.sessionId.trim(),
      topics: input.topics.map((t) => t.name.trim()).filter(Boolean),
      exclude_prompts: input.excludePrompts ?? [],
    },
    { timeout: GENERATE_PROMPTS_TIMEOUT_MS },
  );
  return promptRowsFromGenerated(input.topics, data.items ?? []);
}

/** UI Step 3→完成：落库；有有效订阅时触发首次采样 */
export async function finalizeSetup(input: FinalizeSetupInput): Promise<{
  subjectId: string;
  samplingJobId: string | null;
}> {
  const { topics } = buildFinalizePayload(input);
  const { data } = await api.post<{ subject_id: string; sampling_job_id: string | null }>(
    "/subjects/setup/finalize",
    {
      session_id: input.sessionId.trim(),
      topics,
    },
  );
  return { subjectId: data.subject_id, samplingJobId: data.sampling_job_id ?? null };
}
