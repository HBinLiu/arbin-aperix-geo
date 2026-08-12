export {
  clearSetupCache,
  defaultSetupCache,
  loadSetupCache,
  saveSetupCache,
} from "@/lib/setup/cache";
export {
  competitorDuplicateMessage,
  competitorRowDomainKey,
  displayNameFromDomainInput,
  findCompetitorDuplicate,
  matchesSubjectIdentity,
  newCompetitorRow,
  rowsToPersist,
} from "@/lib/setup/competitors";
export type { SubjectIdentity } from "@/lib/setup/competitors";
export { buildFinalizePayload } from "@/lib/setup/finalize";
export { setupStepHeader, setupVerticalStep } from "@/lib/setup/headers";
export { SETUP_LANGUAGES, SETUP_REGIONS } from "@/lib/setup/options";
export {
  maxPromptCount,
  newPromptRow,
  promptRowsFromGenerated,
  selectedPromptRows,
} from "@/lib/setup/prompts";
export {
  hasAnyBrandMaterial,
  MAX_SETUP_UPLOAD_FILES,
  setupCompetitorStep,
  setupMaxStep,
  setupPromptsStep,
  setupStepLabels,
  setupTopicsStep,
} from "@/lib/setup/flow";
export {
  MAX_TOPICS,
  newTopicRow,
  selectedTopicNames,
  selectedTopicRows,
  topicRowsFromSetupTopics,
} from "@/lib/setup/topics";
