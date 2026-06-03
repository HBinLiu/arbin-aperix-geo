export const queryKeys = {
  subjects: ["subjects"] as const,
  me: ["auth", "me"] as const,
  overview: (subjectId: string, from: string, to: string) =>
    ["overview", subjectId, from, to] as const,
  rank: (subjectId: string, from: string, to: string) =>
    ["rank", subjectId, from, to] as const,
  analysisOverview: (
    subjectId: string,
    from: string,
    to: string,
    topicId = "all",
    platformId = "all",
  ) => ["analysis-overview", subjectId, from, to, topicId, platformId] as const,
  analysisRank: (
    subjectId: string,
    from: string,
    to: string,
    topicId = "all",
    platformId = "all",
  ) => ["analysis-rank", subjectId, from, to, topicId, platformId] as const,
  analysisDailyVisibility: (
    subjectId: string,
    from: string,
    to: string,
    topicId = "all",
    platformId = "all",
  ) => ["analysis-daily-visibility", subjectId, from, to, topicId, platformId] as const,
  analysisPrompts: (subjectId: string, from: string, to: string) =>
    ["analysis-prompts", subjectId, from, to] as const,
  analysisPlatforms: (subjectId: string, from: string, to: string) =>
    ["analysis-platforms", subjectId, from, to] as const,
  analysisCitationRank: (subjectId: string, from: string, to: string) =>
    ["analysis-citation-rank", subjectId, from, to] as const,
  analysisDailySentiment: (subjectId: string, from: string, to: string) =>
    ["analysis-daily-sentiment", subjectId, from, to] as const,
  pipelineStatus: (subjectId: string) => ["pipeline-status", subjectId] as const,
  samplingJob: (jobId: string) => ["sampling-job", jobId] as const,
  samplingPlatforms: ["sampling-platforms"] as const,
  brandCompetitors: (subjectId: string) => ["brand-competitors", subjectId] as const,
  brandPrompts: (subjectId: string) => ["brand-prompts", subjectId] as const,
  subjectTopics: (subjectId: string) => ["subject-topics", subjectId] as const,
};
