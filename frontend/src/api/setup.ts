import {
  api,
  DISCOVER_PROFILE_TIMEOUT_MS,
  GENERATE_PROMPTS_TIMEOUT_MS,
} from "@/api/client";
import {
  buildFinalizePayload,
  promptRowsFromGenerated,
  rowsFromDiscover,
  rowsToPersist,
  topicRowsFromMonitoringTopics,
} from "@/lib/setup";
import type {
  CompetitorRow,
  FinalizeSetupInput,
  GeneratedPromptItem,
  PromptRow,
  SubjectMode,
  TopicRow,
} from "@/types";

export type DiscoverSetupResult = {
  sessionId: string;
  competitorRows: CompetitorRow[];
};

/** UI Step 0→1：微观画像 + 竞品发现 */
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
    competitors: {
      domain: string;
      website_url?: string;
      brand: string;
    }[];
  }>(
    "/subjects/setup/discover",
    {
      type: input.mode,
      ...(domain ? { domain } : {}),
      ...(brand ? { brand } : {}),
      region: input.region,
      language: input.language,
      ...(sessionId ? { session_id: sessionId } : {}),
    },
    { timeout: DISCOVER_PROFILE_TIMEOUT_MS },
  );
  return {
    sessionId: data.session_id,
    competitorRows: rowsFromDiscover(data.competitors ?? []),
  };
}

/** UI Step 1→2：用户确认竞品后生成监测主题 */
export async function generateSetupTopics(input: {
  sessionId: string;
  mode: SubjectMode;
  competitorRows: CompetitorRow[];
}): Promise<{ topicRows: TopicRow[] }> {
  const { competitors } = rowsToPersist(input.mode, input.competitorRows);
  const { data } = await api.post<{ monitoring_topics: string[] }>(
    "/subjects/setup/topics",
    {
      session_id: input.sessionId.trim(),
      competitors,
    },
    { timeout: GENERATE_PROMPTS_TIMEOUT_MS },
  );
  return {
    topicRows: topicRowsFromMonitoringTopics(data.monitoring_topics ?? []),
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

/** UI Step 3→完成：落库并触发首次采样 */
export async function finalizeSetup(input: FinalizeSetupInput): Promise<{
  subjectId: string;
  samplingJobId: string;
}> {
  const { topics } = buildFinalizePayload(input);
  const { data } = await api.post<{ subject_id: string; sampling_job_id: string }>(
    "/subjects/setup/finalize",
    {
      session_id: input.sessionId.trim(),
      topics,
    },
  );
  return { subjectId: data.subject_id, samplingJobId: data.sampling_job_id };
}
