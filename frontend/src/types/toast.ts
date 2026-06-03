export type ToastType = "error" | "success" | "info";

export type ToastItem = {
  id: string;
  message: string;
  type: ToastType;
};
