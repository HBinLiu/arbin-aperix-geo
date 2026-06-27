import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { bindUserPhone, sendBindCode } from "@/api/auth";
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
import type { User } from "@/types";

type BindPhoneDialogProps = {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function BindPhoneDialog({ user, open, onOpenChange }: BindPhoneDialogProps) {
  const queryClient = useQueryClient();
  const { cooldown, startCooldown, resetCooldown } = useOtpCooldown();
  const [phone, setPhone] = React.useState("");
  const [code, setCode] = React.useState("");
  const [info, setInfo] = React.useState<string | null>(null);
  const [sending, setSending] = React.useState(false);

  const bound = Boolean(user.phone?.trim());

  React.useEffect(() => {
    if (open) return;
    setPhone("");
    setCode("");
    setInfo(null);
    resetCooldown();
  }, [open, resetCooldown]);

  const mutation = useMutation({
    mutationFn: bindUserPhone,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
      toast.success(bound ? "手机号已更换" : "手机号已绑定");
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
      const data = await sendBindCode({ channel: "phone", target });
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
    mutation.mutate({ target: phone.trim(), code: code.trim() });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={mutation.isPending}>
      <DialogContent className="max-w-md">
        <form onSubmit={submit}>
          <DialogBody className="space-y-4 pb-0">
            <DialogHeader>
              <div>
                <DialogTitle>{bound ? "更换手机号" : "绑定手机号"}</DialogTitle>
                <DialogDescription>
                  {bound ? `当前手机号：${user.phone}` : "验证新手机号后即可绑定。"}
                </DialogDescription>
              </div>
              <DialogClose />
            </DialogHeader>

            <Input
              className="h-11"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="新手机号"
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
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              确认
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
