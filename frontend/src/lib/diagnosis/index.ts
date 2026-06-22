import type { DiagnosisStatus } from "@/types";

export const DIAGNOSIS_STATUS_LABELS: Record<DiagnosisStatus, string> = {
  excellent: "优秀",
  good: "良好",
  improvement: "待改善",
  critical: "亟需改善",
};
