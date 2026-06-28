export type NotificationCategory = "billing" | "pipeline" | "subscription" | "system";

export type UserNotification = {
  id: string;
  category: NotificationCategory;
  title: string;
  body: string;
  action_url: string;
  read: boolean;
  created_at: string;
};

export type NotificationList = {
  items: UserNotification[];
  unread_count: number;
};
