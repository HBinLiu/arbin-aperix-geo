import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { inviteTenantMember, sendInviteCode } from "@/api/members";
import { OtpCodeField } from "@/components/profile/OtpCodeField";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useOtpCooldown } from "@/hooks/useOtpCooldown";
import { queryKeys } from "@/lib/queries";
import { toast } from "@/lib/toast";

type InviteMemberDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function InviteMemberDialog({ open, onOpenChange }: InviteMemberDialogProps) {
  const queryClient = useQueryClient();
  const { cooldown, startCooldown, resetCooldown } = useOtpCooldown();
  const [phone, setPhone] = React.useState("");
  const [code, setCode] = React.useState("");
  const [info, setInfo] = React.useState<string | null>(null);
  const [sending, setSending] = React.useState(false);

  React.useEffect(() => {
    if (open) return;
    setPhone("");
    setCode("");
    setInfo(null);
    resetCooldown();
  }, [open, resetCooldown]);

  const mutation = useMutation({
    mutationFn: inviteTenantMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.tenantMembers });
      toast.success("成员已加入工作区");
      onOpenChange(false);
    },
  });

  const sendCode = async () => {
    const target = phone.trim();
    if (!target) {
      toast.error("请输入手机号");
      return;
    }
    setInfo(null);
    setSending(true);
    try {
      const data = await sendInviteCode(target);
      startCooldown(60);
      if (data.dev_code) {
        setCode(String(data.dev_code));
      } else if (data.message) {
        setInfo(data.message);
      }
    } catch {
      /* API 拦截器已 toast */
    } finally {
      setSending(false);
    }
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    mutation.mutate({ phone: phone.trim(), code: code.trim() });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={mutation.isPending}>
      <DialogContent className="max-w-md">
        <form onSubmit={submit}>
          <DialogBody className="space-y-4 pb-0">
            <DialogHeader>
              <div>
                <DialogTitle>邀请成员</DialogTitle>
                <DialogDescription>
                  向成员手机号发送验证码，验证通过后将直接加入当前工作区。
                </DialogDescription>
              </div>
              <DialogClose />
            </DialogHeader>

            <Input
              className="h-11"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="成员手机号"
              autoComplete="tel"
              required
            />
            <OtpCodeField
              value={code}
              onChange={setCode}
              cooldown={cooldown}
              sending={sending}
              onSend={sendCode}
            />
            {info ? <p className="text-muted-foreground text-sm">{info}</p> : null}
          </DialogBody>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              确认邀请
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
