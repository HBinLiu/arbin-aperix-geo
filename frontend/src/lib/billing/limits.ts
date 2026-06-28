import type { TenantSubscription } from "@/types/billing";

export const DEFAULT_MAX_COMPETITORS = 10;
export const DEFAULT_MAX_PLATFORMS = 3;

function positiveLimit(value: number | undefined | null, fallback: number): number {
  if (value != null && value > 0) return value;
  return fallback;
}

export function maxCompetitorsPerSubject(subscription?: TenantSubscription | null): number {
  return positiveLimit(subscription?.limits.max_per_competitors, DEFAULT_MAX_COMPETITORS);
}

export function maxPlatformsPerSubject(subscription?: TenantSubscription | null): number {
  return positiveLimit(subscription?.limits.max_per_platforms, DEFAULT_MAX_PLATFORMS);
}

export function maxSubjects(subscription?: TenantSubscription | null): number {
  return positiveLimit(subscription?.limits.max_subjects, 0);
}

export function isAtSubjectLimit(subscription?: TenantSubscription | null): boolean {
  if (subscription == null) return false;
  return subscription.usage.subjects_count >= subscription.limits.max_subjects;
}
