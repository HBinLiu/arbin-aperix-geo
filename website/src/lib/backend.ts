const DEFAULT_API_BASE = "http://127.0.0.1:8000/api/v1";

export function backendApiBase(): string {
  return (import.meta.env.BACKEND_API_URL || DEFAULT_API_BASE).replace(/\/$/, "");
}
