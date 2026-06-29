import { useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Calendar,
  Mail,
  MessageCircle,
  Phone,
  UserRound,
  type LucideIcon,
} from "lucide-react";

import { updateUserNotifications } from "@/api/auth";
import { BindEmailDialog } from "@/components/profile/BindEmailDialog";
import { BindPhoneDialog } from "@/components/profile/BindPhoneDialog";
import { BindWechatDialog } from "@/components/profile/BindWechatDialog";
import { ChangePasswordDialog } from "@/components/profile/ChangePasswordDialog";
import { ProfileSection } from "@/components/profile/ProfileSection";
import { ActionTooltip } from "@/components/common/ActionTooltip";
import { UserAvatar } from "@/components/user/UserAvatar";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { formatPromptCreatedAt } from "@/lib/prompt";
import { queryKeys } from "@/lib/queries";
import { toast } from "@/lib/toast";
import type { UserNotificationSettings } from "@/types";
import { cn } from "@/lib/utils";

function ProfileInfoRow({
  icon: Icon,
  label,
  children,
  action,
  className,
}: {
  icon: LucideIcon;
  label: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-[9rem_minmax(0,1fr)_5rem] items-center gap-x-4 px-4 py-4",
        className,
      )}
    >
      <span className="text-muted-foreground inline-flex items-center gap-2 text-sm">
        <Icon className="size-4 shrink-0" aria-hidden />
        {label}
      </span>
      <div className="min-w-0 flex items-center text-left text-sm">{children}</div>
      <div className="shrink-0 text-center text-sm">{action}</div>
    </div>
  );
}

function ProfileBindAction({
  label = "绑定",
  onClick,
}: {
  label?: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-primary text-sm font-medium transition-colors hover:underline"
    >
      {label}
    </button>
  );
}

function profileBindableContent(value?: string | null) {
  const trimmed = value?.trim();
  if (trimmed) {
    return <span className="text-foreground break-all">{trimmed}</span>;
  }
  return <span className="text-muted-foreground">暂未绑定</span>;
}

function profileContactAction(bound: boolean, onAction: () => void) {
  return <ProfileBindAction label={bound ? "更换" : "绑定"} onClick={onAction} />;
}

function ProfileToggleRow({
  icon: Icon,
  label,
  checked,
  onCheckedChange,
  disabled,
  disabledTooltip,
}: {
  icon: LucideIcon;
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
  disabledTooltip?: string;
}) {
  const switchControl = (
    <Switch checked={checked} onCheckedChange={onCheckedChange} disabled={disabled} />
  );

  return (
    <div className="grid grid-cols-[9rem_minmax(0,1fr)_5rem] items-center gap-x-4 px-4 py-4">
      <span className="text-muted-foreground inline-flex items-center gap-2 text-sm">
        <Icon className="size-4 shrink-0" aria-hidden />
        {label}
      </span>
      <div aria-hidden />
      <div className="flex shrink-0 justify-center">
        {disabled && disabledTooltip ? (
          <ActionTooltip label={disabledTooltip}>
            <span className="inline-flex cursor-not-allowed">{switchControl}</span>
          </ActionTooltip>
        ) : (
          switchControl
        )}
      </div>
    </div>
  );
}

/** 账户设置 · 账户信息 */
export function AccountSettingsView() {
  const queryClient = useQueryClient();
  const { user } = useDashboardContext();
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [phoneOpen, setPhoneOpen] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [wechatOpen, setWechatOpen] = useState(false);

  const registeredAt = user.created_at ? formatPromptCreatedAt(user.created_at) : "—";
  const phoneBound = Boolean(user.phone?.trim());
  const emailBound = Boolean(user.email?.trim());
  const wechatBound = Boolean(user.wechat.open_id.trim());
  const wechatDisplay = user.wechat.nick_name.trim() || (wechatBound ? "已绑定" : null);

  const notificationMutation = useMutation({
    mutationFn: updateUserNotifications,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
      toast.success("通知设置已更新");
    },
  });

  const setNotification = (key: keyof UserNotificationSettings, checked: boolean) => {
    notificationMutation.mutate({ [key]: checked });
  };

  return (
    <>
      <div className="flex flex-col gap-4 px-4 py-10 sm:px-[5%] md:px-[10%] lg:px-[15%] xl:px-[20%] 2xl:px-[25%]">
        <ProfileSection
          title="账户信息"
          headerAction={
            <Button type="button" variant="outline" size="sm" onClick={() => setPasswordOpen(true)}>
              {user.has_password ? "更换密码" : "设置密码"}
            </Button>
          }
        >
          <ProfileInfoRow className="py-2" icon={UserRound} label="头像">
            <UserAvatar size="md" seed={user.id} />
          </ProfileInfoRow>
          <ProfileInfoRow
            icon={Phone}
            label="手机号"
            action={profileContactAction(phoneBound, () => setPhoneOpen(true))}
          >
            {profileBindableContent(user.phone)}
          </ProfileInfoRow>
          <ProfileInfoRow
            icon={Mail}
            label="电子邮箱"
            action={profileContactAction(emailBound, () => setEmailOpen(true))}
          >
            {profileBindableContent(user.email)}
          </ProfileInfoRow>
          <ProfileInfoRow
            icon={MessageCircle}
            label="绑定微信"
            action={profileContactAction(wechatBound, () => setWechatOpen(true))}
          >
            {profileBindableContent(wechatDisplay)}
          </ProfileInfoRow>
          <ProfileInfoRow icon={Calendar} label="注册时间">
            <span className="text-foreground tabular-nums">{registeredAt}</span>
          </ProfileInfoRow>
        </ProfileSection>

        <ProfileSection title="通知设置">
          <ProfileToggleRow
            icon={Bell}
            label="站内通知"
            checked={user.notifications.in_app}
            onCheckedChange={(checked) => setNotification("in_app", checked)}
          />
          <ProfileToggleRow
            icon={Mail}
            label="邮件通知"
            checked={user.notifications.email}
            onCheckedChange={(checked) => setNotification("email", checked)}
            disabled={!emailBound}
            disabledTooltip={!emailBound ? "请先绑定电子邮箱" : undefined}
          />
          <ProfileToggleRow
            icon={MessageCircle}
            label="微信通知"
            checked={user.notifications.wechat}
            onCheckedChange={(checked) => setNotification("wechat", checked)}
            disabled={!wechatBound}
            disabledTooltip={!wechatBound ? "请先绑定微信" : undefined}
          />
        </ProfileSection>
      </div>

      <ChangePasswordDialog user={user} open={passwordOpen} onOpenChange={setPasswordOpen} />
      <BindPhoneDialog user={user} open={phoneOpen} onOpenChange={setPhoneOpen} />
      <BindEmailDialog user={user} open={emailOpen} onOpenChange={setEmailOpen} />
      <BindWechatDialog user={user} open={wechatOpen} onOpenChange={setWechatOpen} />
    </>
  );
}
