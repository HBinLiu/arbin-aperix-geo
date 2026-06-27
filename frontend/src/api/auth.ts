import { api } from "@/api/client";
import type {
  BindEmailInput,
  BindPhoneInput,
  ChangePasswordInput,
  User,
  UserNotificationSettingsUpdate,
  WechatBindDevInput,
} from "@/types";

type SendCodePurpose = "login" | "register";
type SendCodeChannel = "email" | "phone";
type BindCodeChannel = "email" | "phone";

export type SendCodeResult = {
  dev_code?: string | number;
  message?: string;
};

type AccessTokenResult = {
  access_token: string;
};

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

export async function updateUserNotifications(
  input: UserNotificationSettingsUpdate,
): Promise<User> {
  const { data } = await api.patch<User>("/auth/me/notifications", input);
  return data;
}

export async function changeUserPassword(input: ChangePasswordInput): Promise<User> {
  const { data } = await api.patch<User>("/auth/me/password", input);
  return data;
}

export async function sendBindCode(input: {
  channel: BindCodeChannel;
  target: string;
}): Promise<SendCodeResult> {
  const { data } = await api.post<SendCodeResult>("/auth/me/send-bind-code", input);
  return data;
}

export async function bindUserPhone(input: BindPhoneInput): Promise<User> {
  const { data } = await api.patch<User>("/auth/me/phone", input);
  return data;
}

export async function bindUserEmail(input: BindEmailInput): Promise<User> {
  const { data } = await api.patch<User>("/auth/me/email", input);
  return data;
}

export async function unbindUserWechat(): Promise<User> {
  const { data } = await api.post<User>("/auth/me/wechat/unbind");
  return data;
}

export async function bindUserWechatDev(input: WechatBindDevInput): Promise<User> {
  const { data } = await api.post<User>("/auth/me/wechat/bind-dev", input);
  return data;
}

export async function sendAuthCode(input: {
  purpose: SendCodePurpose;
  channel: SendCodeChannel;
  target: string;
}): Promise<SendCodeResult> {
  const { data } = await api.post<SendCodeResult>("/auth/send-code", input);
  return data;
}

export async function loginWithPassword(input: {
  email: string;
  password: string;
}): Promise<AccessTokenResult> {
  const { data } = await api.post<AccessTokenResult>("/auth/login", input);
  return data;
}

export async function loginWithOtp(input: {
  channel: "phone";
  target: string;
  code: string;
}): Promise<AccessTokenResult> {
  const { data } = await api.post<AccessTokenResult>("/auth/login-with-otp", input);
  return data;
}

export async function registerWithOtp(input: {
  tenant_name: string;
  channel: "email";
  target: string;
  code: string;
  password: string;
}): Promise<AccessTokenResult> {
  const { data } = await api.post<AccessTokenResult>("/auth/register-with-otp", input);
  return data;
}
