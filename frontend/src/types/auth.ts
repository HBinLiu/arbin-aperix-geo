export type UserWechat = {
  nick_name: string;
  open_id: string;
  union_id: string;
};

export type UserNotificationSettings = {
  in_app: boolean;
  email: boolean;
  wechat: boolean;
};

export type User = {
  id: string;
  tenant_id: string;
  email: string;
  phone: string;
  role: "admin" | "member" | "readonly";
  has_password: boolean;
  created_at: string;
  wechat: UserWechat;
  notifications: UserNotificationSettings;
};

export type UserNotificationSettingsUpdate = Partial<UserNotificationSettings>;

export type ChangePasswordInput = {
  current_password?: string;
  new_password: string;
};

export type BindPhoneInput = {
  target: string;
  code: string;
};

export type BindEmailInput = {
  target: string;
  code: string;
  password?: string;
};

export type WechatBindDevInput = {
  nick_name: string;
  open_id?: string;
  union_id?: string;
};
