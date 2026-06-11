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
  topicRowsFromDiscover,
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
  const { data } = await api.post<{ session_id: string; micro_keywords: string[] }>(
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
    topicRows: topicRowsFromDiscover(data.micro_keywords),
  };
}

export async function discoverCompetitors(input: {
  mode: SubjectMode;
  sessionId: string;
  microKeywords: string[];
}): Promise<{ competitorRows: CompetitorRow[]; topicRows?: TopicRow[] }> {
  const { data } = await api.post<{
    competitors: { domain: string; website_url?: string; brand: string; summary: string }[];
    micro_keywords?: string[];
  }>(
    "/subjects/discover-competitors",
    { session_id: input.sessionId, micro_keywords: input.microKeywords },
    { timeout: DISCOVER_COMPETITORS_TIMEOUT_MS },
  );
  return {
    competitorRows: rowsFromDiscover(data.competitors ?? []),
    topicRows: data.micro_keywords?.length ? topicRowsFromDiscover(data.micro_keywords) : undefined,
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
      topics: input.topics.map((t) => t.name.trim()),
      competitors: input.competitorLabels,
      exclude_prompts: (input.excludePrompts ?? []).map((text) => text.trim()).filter(Boolean),
    },
    { timeout: GENERATE_PROMPTS_TIMEOUT_MS },
  );
  return promptRowsFromGenerated(input.topics, data.items);
}

export async function finalizeSetup(input: FinalizeSetupInput): Promise<{
  subject: Subject;
  samplingJobId: string;
}> {
  const { data } = await api.post<{ subject: Subject; sampling_job_id: string }>(
    "/subjects/setup-finalize",
    buildFinalizePayload(input),
  );
  return { subject: data.subject, samplingJobId: data.sampling_job_id };
}
