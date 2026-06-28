import { api } from "@/api/client";
import type { NotificationList } from "@/types/notifications";

export async function fetchNotifications(limit = 20): Promise<NotificationList> {
  const { data } = await api.get<NotificationList>("/notifications", { params: { limit } });
  return data;
}

export async function fetchUnreadNotificationCount(): Promise<number> {
  const { data } = await api.get<{ unread_count: number }>("/notifications/unread-count");
  return data.unread_count;
}

export async function markNotificationRead(notificationId: string): Promise<void> {
  await api.patch(`/notifications/${notificationId}/read`);
}

export async function markAllNotificationsRead(): Promise<number> {
  const { data } = await api.post<{ marked: number }>("/notifications/read-all");
  return data.marked;
}
