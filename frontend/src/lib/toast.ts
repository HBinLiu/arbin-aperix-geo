import { toast as sonnerToast } from "sonner";

const DEFAULT_DURATION_MS = 5200;

function push(type: "error" | "success" | "info", message: string, durationMs = DEFAULT_DURATION_MS) {
  const trimmed = message.trim();
  if (!trimmed) return;

  const options = { duration: durationMs };
  if (type === "error") sonnerToast.error(trimmed, options);
  else if (type === "success") sonnerToast.success(trimmed, options);
  else sonnerToast.info(trimmed, options);
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
  dismiss(id?: string | number) {
    sonnerToast.dismiss(id);
  },
};
