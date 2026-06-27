import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { changeUserPassword } from "@/api/auth";
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
import { queryKeys } from "@/lib/queries";
import { PASSWORD_RULE_HINT, validatePasswordStrength } from "@/lib/password";
import { toast } from "@/lib/toast";
import type { User } from "@/types";

type ChangePasswordDialogProps = {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function ChangePasswordDialog({ user, open, onOpenChange }: ChangePasswordDialogProps) {
  const queryClient = useQueryClient();
  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");

  React.useEffect(() => {
    if (open) return;
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  }, [open]);

  const mutation = useMutation({
    mutationFn: changeUserPassword,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
      toast.success(user.has_password ? "密码已更新" : "登录密码已设置");
      onOpenChange(false);
    },
  });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error("两次输入的新密码不一致");
      return;
    }
    const passwordError = validatePasswordStrength(newPassword);
    if (passwordError) {
      toast.error(passwordError);
      return;
    }
    if (user.has_password && !currentPassword.trim()) {
      toast.error("请输入当前密码");
      return;
    }
    mutation.mutate({
      current_password: user.has_password ? currentPassword : undefined,
      new_password: newPassword,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={mutation.isPending}>
      <DialogContent className="max-w-md">
        <form onSubmit={submit}>
          <DialogBody className="space-y-4 pb-0">
            <DialogHeader>
              <div>
                <DialogTitle>{user.has_password ? "更换密码" : "设置登录密码"}</DialogTitle>
                <DialogDescription>
                  {user.has_password
                    ? "请输入当前密码与新密码。"
                    : "设置密码后，可使用邮箱与密码登录。"}
                </DialogDescription>
              </div>
              <DialogClose />
            </DialogHeader>

            {user.has_password ? (
              <Input
                className="h-11"
                type="password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                placeholder="当前密码"
                autoComplete="current-password"
                required
              />
            ) : null}
            <Input
              className="h-11"
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="新密码"
              autoComplete="new-password"
              required
            />
            <p className="text-muted-foreground text-xs leading-relaxed pl-1">{PASSWORD_RULE_HINT}</p>
            <Input
              className="h-11"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="确认新密码"
              autoComplete="new-password"
              required
            />
          </DialogBody>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              取消
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              保存
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
