import type { ToastItem, ToastType } from "@/types";

const listeners = new Set<(items: ToastItem[]) => void>();
let queue: ToastItem[] = [];

const MAX_TOASTS = 5;
const DEFAULT_DURATION_MS = 5200;

function emit() {
  const snapshot = [...queue];
  listeners.forEach((listener) => listener(snapshot));
}

function dismiss(id: string) {
  queue = queue.filter((item) => item.id !== id);
  emit();
}

function push(type: ToastType, message: string, durationMs = DEFAULT_DURATION_MS) {
  const trimmed = message.trim();
  if (!trimmed) return;

  const id = crypto.randomUUID();
  queue = [...queue, { id, message: trimmed, type }].slice(-MAX_TOASTS);
  emit();

  window.setTimeout(() => dismiss(id), durationMs);
}

export const toast = {
  error(message: string, durationMs?: number) {
    push("error", message, durationMs);
  },
  success(message: string, durationMs?: number) {
    push("success", message, durationMs);
  },
  info(message: string, durationMs?: number) {
    push("info", message, durationMs);
  },
  dismiss,
};

export function subscribeToasts(listener: (items: ToastItem[]) => void): () => void {
  listeners.add(listener);
  listener([...queue]);
  return () => listeners.delete(listener);
}
