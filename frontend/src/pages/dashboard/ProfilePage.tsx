import { useLocation } from "react-router-dom";

import { AccountSettingsView } from "@/components/profile/AccountSettingsView";
import { MembersView } from "@/components/profile/MembersView";
import { profileTabFromPathname } from "@/lib/profile/nav";

/** 账户设置 · 账户 / 成员 */
export function ProfileContent() {
  const { pathname } = useLocation();
  const activeTab = profileTabFromPathname(pathname);

  if (activeTab === "members") {
    return <MembersView />;
  }

  return <AccountSettingsView />;
}
