import {
  api,
  DISCOVER_COMPETITORS_TIMEOUT_MS,
  DISCOVER_PROFILE_TIMEOUT_MS,
  GENERATE_PROMPTS_TIMEOUT_MS,
} from "@/api/client";
import type { Subject } from "@/types";
import type {
  CompetitorRow,
  FinalizeSetupInput,
  GeneratedPromptItem,
  PromptRow,
  SubjectMode,
  TopicRow,
} from "@/types";
import {
  buildFinalizePayload,
  promptRowsFromGenerated,
  rowsFromDiscover,
  topicRowsFromMonitoringTopics,
} from "@/lib/setup";

export type DiscoverProfileResult = {
  sessionId: string;
  topicRows: TopicRow[];
};

export async function discoverProfile(input: {
  mode: SubjectMode;
  domain: string;
  brand: string;
  region: string;
  language: string;
}): Promise<DiscoverProfileResult> {
  const domain = input.domain.trim();
  const brand = input.brand.trim();
  const { data } = await api.post<{
    session_id: string;
    monitoring_topics: string[];
  }>(
    "/subjects/discover-profile",
    {
      type: input.mode,
      ...(domain ? { domain } : {}),
      ...(brand ? { brand } : {}),
      region: input.region,
      language: input.language,
    },
    { timeout: DISCOVER_PROFILE_TIMEOUT_MS },
  );
  return {
    sessionId: data.session_id,
    topicRows: topicRowsFromMonitoringTopics(data.monitoring_topics),
  };
}

export async function discoverCompetitors(input: {
  sessionId: string;
  monitoringTopics: string[];
}): Promise<{ competitorRows: CompetitorRow[] }> {
  const { data } = await api.post<{
    competitors: { domain: string; website_url?: string; brand: string; summary: string }[];
  }>(
    "/subjects/discover-competitors",
    {
      session_id: input.sessionId,
      monitoring_topics: input.monitoringTopics,
    },
    { timeout: DISCOVER_COMPETITORS_TIMEOUT_MS },
  );
  return {
    competitorRows: rowsFromDiscover(data.competitors ?? []),
  };
}

export async function generateSetupPrompts(input: {
  sessionId: string;
  topics: TopicRow[];
  competitorLabels: string[];
  excludePrompts?: string[];
}): Promise<PromptRow[]> {
  const { data } = await api.post<{ items: { topic: string; prompts: GeneratedPromptItem[] }[] }>(
    "/subjects/generate-prompts",
    {
      session_id: input.sessionId,
      topics: input.topics.map((t) => t.name.trim()).filter(Boolean),
      competitors: input.competitorLabels,
      exclude_prompts: input.excludePrompts ?? [],
    },
    { timeout: GENERATE_PROMPTS_TIMEOUT_MS },
  );
  return promptRowsFromGenerated(input.topics, data.items ?? []);
}

export async function finalizeSetup(input: FinalizeSetupInput): Promise<{
  subject: Subject;
  samplingJobId: string;
}> {
  const payload = buildFinalizePayload(input);
  const { data } = await api.post<{ subject: Subject; sampling_job_id: string }>(
    "/subjects/setup-finalize",
    payload,
  );
  return { subject: data.subject, samplingJobId: data.sampling_job_id };
}
