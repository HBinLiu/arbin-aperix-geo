export type TenantMemberRole = "admin" | "member" | "readonly";

export type TenantMember = {
  id: string;
  phone: string;
  role: TenantMemberRole;
  is_active: boolean;
  created_at: string;
};

export type TenantMembersResponse = {
  items: TenantMember[];
};

export type InviteMemberInput = {
  phone: string;
  code: string;
  role?: "member" | "readonly";
};
