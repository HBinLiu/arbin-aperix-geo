import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchNotifications,
  fetchUnreadNotificationCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/api/notifications";
import { queryKeys } from "@/lib/queries";

const POLL_MS = 60_000;

export function useNotificationUnreadCount(enabled = true) {
  return useQuery({
    queryKey: queryKeys.notificationUnreadCount,
    queryFn: fetchUnreadNotificationCount,
    enabled,
    staleTime: 30_000,
    refetchInterval: POLL_MS,
  });
}

export function useNotifications(open: boolean) {
  return useQuery({
    queryKey: queryKeys.notifications,
    queryFn: () => fetchNotifications(20),
    enabled: open,
    staleTime: 15_000,
  });
}

export function useNotificationActions() {
  const queryClient = useQueryClient();

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.notifications });
    void queryClient.invalidateQueries({ queryKey: queryKeys.notificationUnreadCount });
  };

  const markRead = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: invalidate,
  });

  const markAllRead = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidate,
  });

  return { markRead, markAllRead };
}
