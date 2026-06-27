import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { bindUserWechatDev, unbindUserWechat } from "@/api/auth";
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
import { toast } from "@/lib/toast";
import type { User } from "@/types";

type BindWechatDialogProps = {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const isDevEnv = import.meta.env.DEV;

export function BindWechatDialog({ user, open, onOpenChange }: BindWechatDialogProps) {
  const queryClient = useQueryClient();
  const [nickName, setNickName] = React.useState("");

  const bound = Boolean(user.wechat.open_id.trim());
  const displayName = user.wechat.nick_name.trim() || (bound ? "已绑定" : "");

  React.useEffect(() => {
    if (open) return;
    setNickName("");
  }, [open]);

  const bindMutation = useMutation({
    mutationFn: bindUserWechatDev,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
      toast.success(bound ? "微信已更换" : "微信已绑定");
      onOpenChange(false);
    },
  });

  const unbindMutation = useMutation({
    mutationFn: unbindUserWechat,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
      toast.success("微信已解绑");
      onOpenChange(false);
    },
  });

  const submitBind = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = nickName.trim();
    if (!trimmed) {
      toast.error("请输入微信昵称");
      return;
    }
    bindMutation.mutate({ nick_name: trimmed });
  };

  const pending = bindMutation.isPending || unbindMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={pending}>
      <DialogContent className="max-w-md">
        <DialogBody className="space-y-4 pb-0">
          <DialogHeader>
            <div>
              <DialogTitle>{bound ? "更换微信" : "绑定微信"}</DialogTitle>
              <DialogDescription>
                {bound
                  ? `当前绑定：${displayName}`
                  : "绑定后可开启微信通知。"}
              </DialogDescription>
            </div>
            <DialogClose />
          </DialogHeader>

          {isDevEnv ? (
            <form id="wechat-bind-form" className="space-y-4" onSubmit={submitBind}>
              <Input
                className="h-11"
                value={nickName}
                onChange={(event) => setNickName(event.target.value)}
                placeholder="微信昵称（开发环境模拟绑定）"
                required
              />
              <p className="text-muted-foreground text-sm">
                生产环境将接入微信 OAuth 扫码绑定；开发环境可直接填写昵称完成模拟绑定。
              </p>
            </form>
          ) : (
            <p className="text-muted-foreground text-sm leading-relaxed">
              微信扫码绑定尚未配置。请联系管理员配置微信开放平台后，在此完成绑定与更换。
            </p>
          )}
        </DialogBody>
        <DialogFooter className="flex-wrap gap-2">
          {bound ? (
            <Button
              type="button"
              variant="outline"
              className="mr-auto"
              disabled={pending}
              onClick={() => unbindMutation.mutate()}
            >
              解绑
            </Button>
          ) : null}
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={pending}>
            取消
          </Button>
          {isDevEnv ? (
            <Button type="submit" form="wechat-bind-form" disabled={pending}>
              {bound ? "更换" : "绑定"}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
