import { api } from "@/api/client";
import type { InviteMemberInput, TenantMember, TenantMembersResponse } from "@/types/members";
import type { SendCodeResult } from "@/api/auth";

export async function fetchTenantMembers(): Promise<TenantMembersResponse> {
  const { data } = await api.get<TenantMembersResponse>("/auth/tenant/members");
  return data;
}

export async function sendInviteCode(phone: string): Promise<SendCodeResult> {
  const { data } = await api.post<SendCodeResult>("/auth/tenant/members/send-invite-code", { phone });
  return data;
}

export async function inviteTenantMember(input: InviteMemberInput): Promise<TenantMember> {
  const { data } = await api.post<TenantMember>("/auth/tenant/members/invite", input);
  return data;
}

export async function removeTenantMember(userId: string): Promise<void> {
  await api.delete(`/auth/tenant/members/${userId}`);
}
