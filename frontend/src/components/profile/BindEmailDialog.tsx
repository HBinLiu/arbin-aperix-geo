import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { bindUserEmail, sendBindCode } from "@/api/auth";
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

type BindEmailDialogProps = {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function BindEmailDialog({ user, open, onOpenChange }: BindEmailDialogProps) {
  const queryClient = useQueryClient();
  const { cooldown, startCooldown, resetCooldown } = useOtpCooldown();
  const [email, setEmail] = React.useState("");
  const [code, setCode] = React.useState("");
  const [info, setInfo] = React.useState<string | null>(null);
  const [sending, setSending] = React.useState(false);

  const bound = Boolean(user.email?.trim());

  React.useEffect(() => {
    if (open) return;
    setEmail("");
    setCode("");
    setInfo(null);
    resetCooldown();
  }, [open, resetCooldown]);

  const mutation = useMutation({
    mutationFn: bindUserEmail,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
      toast.success(bound ? "邮箱已更换" : "邮箱已绑定");
      onOpenChange(false);
    },
  });

  const sendCode = async () => {
    const target = email.trim().toLowerCase();
    if (!target) {
      toast.error("请输入邮箱");
      return;
    }
    setInfo(null);
    setSending(true);
    try {
      const data = await sendBindCode({ channel: "email", target });
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
    mutation.mutate({
      target: email.trim().toLowerCase(),
      code: code.trim(),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={mutation.isPending}>
      <DialogContent className="max-w-md">
        <form onSubmit={submit}>
          <DialogBody className="space-y-4 pb-0">
            <DialogHeader>
              <div>
                <DialogTitle>{bound ? "更换邮箱" : "绑定邮箱"}</DialogTitle>
                <DialogDescription>
                  {bound ? `当前邮箱：${user.email}` : "验证邮箱后可接收邮件通知。"}
                </DialogDescription>
              </div>
              <DialogClose />
            </DialogHeader>

            <Input
              className="h-11"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="新邮箱"
              autoComplete="email"
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
