import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { QRCodeSVG } from "qrcode.react";

import {
  bindUserWechatDev,
  createWechatBindQr,
  fetchWechatBindQrStatus,
  unbindUserWechat,
} from "@/api/auth";
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

type QrState = {
  ticketId: string;
  authorizeUrl: string;
  status: "pending" | "bound" | "failed" | "expired";
  error: string;
};

export function BindWechatDialog({ user, open, onOpenChange }: BindWechatDialogProps) {
  const queryClient = useQueryClient();
  const [nickName, setNickName] = React.useState("");
  const [mode, setMode] = React.useState<"loading" | "qr" | "dev" | "unavailable">("loading");
  const [qr, setQr] = React.useState<QrState | null>(null);

  const bound = Boolean(user.wechat.open_id.trim());
  const displayName = user.wechat.nick_name.trim() || (bound ? "已绑定" : "");

  const resetLocal = React.useCallback(() => {
    setNickName("");
    setQr(null);
    setMode("loading");
  }, []);

  React.useEffect(() => {
    if (!open) {
      resetLocal();
      return;
    }

    let cancelled = false;
    const start = async () => {
      setMode("loading");
      try {
        const data = await createWechatBindQr();
        if (cancelled) return;
        const authorizeUrl = data.authorize_url || data.qrcode_url || "";
        if (!authorizeUrl) throw new Error("missing authorize_url");
        setQr({
          ticketId: data.ticket_id,
          authorizeUrl,
          status: "pending",
          error: "",
        });
        setMode("qr");
      } catch (error) {
        if (cancelled) return;
        const status = isAxiosError(error) ? error.response?.status : undefined;
        if (status === 503 && isDevEnv) {
          setMode("dev");
          return;
        }
        setMode(isDevEnv ? "dev" : "unavailable");
      }
    };
    void start();
    return () => {
      cancelled = true;
    };
  }, [open, isDevEnv, resetLocal]);

  React.useEffect(() => {
    if (!open || mode !== "qr" || !qr || qr.status !== "pending") return;
    const timer = setInterval(() => {
      void (async () => {
        try {
          const status = await fetchWechatBindQrStatus(qr.ticketId);
          if (status.status === "pending") return;
          setQr((prev) =>
            prev
              ? {
                  ...prev,
                  status: status.status,
                  error: status.error || "",
                }
              : prev,
          );
          if (status.status === "bound") {
            queryClient.invalidateQueries({ queryKey: queryKeys.me });
            toast.success(bound ? "微信已更换" : "微信已绑定");
            onOpenChange(false);
          } else if (status.status === "failed") {
            toast.error(status.error || "绑定失败");
          } else if (status.status === "expired") {
            toast.error("二维码已过期，请关闭后重试");
          }
        } catch {
          /* 轮询失败忽略，下一拍重试 */
        }
      })();
    }, 2000);
    return () => clearInterval(timer);
  }, [open, mode, qr, bound, queryClient, onOpenChange]);

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

  const submitDevBind = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = nickName.trim();
    if (!trimmed) {
      toast.error("请输入微信昵称");
      return;
    }
    bindMutation.mutate({ nick_name: trimmed });
  };

  const pending = bindMutation.isPending || unbindMutation.isPending || mode === "loading";

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={pending && mode === "dev"}>
      <DialogContent className="max-w-md">
        <DialogBody className="space-y-4 pb-0">
          <DialogHeader>
            <div>
              <DialogTitle>{bound ? "更换微信" : "绑定微信"}</DialogTitle>
              <DialogDescription>
                {bound ? `当前绑定：${displayName}` : "绑定后可开启微信通知。"}
              </DialogDescription>
            </div>
            <DialogClose />
          </DialogHeader>

          {mode === "loading" ? (
            <p className="text-muted-foreground text-sm">正在生成绑定二维码…</p>
          ) : null}

          {mode === "qr" && qr ? (
            <div className="flex flex-col items-center gap-3 py-2">
              <div className="border-border flex size-48 items-center justify-center border bg-white p-2">
                <QRCodeSVG value={qr.authorizeUrl} size={176} level="M" includeMargin={false} />
              </div>
              <p className="text-muted-foreground text-center text-sm leading-relaxed">
                请用微信扫码并授权，完成后将显示微信昵称。二维码约 5 分钟内有效。
              </p>
              {qr.status === "failed" ? (
                <p className="text-destructive text-sm">{qr.error || "绑定失败"}</p>
              ) : null}
              {qr.status === "expired" ? (
                <p className="text-destructive text-sm">二维码已过期，请关闭后重新打开</p>
              ) : null}
            </div>
          ) : null}

          {mode === "dev" ? (
            <form id="wechat-bind-form" className="space-y-4" onSubmit={submitDevBind}>
              <Input
                className="h-11"
                value={nickName}
                onChange={(event) => setNickName(event.target.value)}
                placeholder="微信昵称（开发环境模拟绑定）"
                required
              />
              <p className="text-muted-foreground text-sm">
                未配置公众号时，开发环境可填写昵称模拟绑定；配置{" "}
                <code className="text-xs">WECHAT_*</code> 与网页授权回调后将改为扫码授权绑定。
              </p>
            </form>
          ) : null}

          {mode === "unavailable" ? (
            <p className="text-muted-foreground text-sm leading-relaxed">
              微信绑定尚未配置。请联系管理员配置服务号（
              <code className="text-xs">WECHAT_APP_ID / SECRET / OAUTH_REDIRECT_URI</code>
              ）后，在此扫码授权完成绑定与更换。
            </p>
          ) : null}
        </DialogBody>
        <DialogFooter className="flex-wrap gap-2">
          {bound ? (
            <Button
              type="button"
              variant="outline"
              className="mr-auto"
              disabled={unbindMutation.isPending}
              onClick={() => unbindMutation.mutate()}
            >
              解绑
            </Button>
          ) : null}
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={unbindMutation.isPending || bindMutation.isPending}
          >
            取消
          </Button>
          {mode === "dev" ? (
            <Button type="submit" form="wechat-bind-form" disabled={bindMutation.isPending}>
              {bound ? "更换" : "绑定"}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
