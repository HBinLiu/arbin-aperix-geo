import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import { fetchPayOrder, prepayPayOrder, simulatePayOrder } from "@/api/billing";
import { formatApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { queryKeys } from "@/lib/queries";
import { toast } from "@/lib/toast";

const POLL_INTERVAL_MS = 2000;

type PayOrderDialogProps = {
  orderId: string | null;
  amountCents: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPaid?: () => void | Promise<void>;
  title?: string;
  description?: string;
};

function formatYuan(amountCents: number): string {
  return (amountCents / 100).toLocaleString("zh-CN", {
    minimumFractionDigits: amountCents % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

export function PayOrderDialog({
  orderId,
  amountCents,
  open,
  onOpenChange,
  onPaid,
  title = "微信支付",
  description = "请使用微信扫一扫完成支付，支付成功后将自动刷新。",
}: PayOrderDialogProps) {
  const queryClient = useQueryClient();
  const [loading, setLoading] = React.useState(false);
  const [simulating, setSimulating] = React.useState(false);
  const [codeUrl, setCodeUrl] = React.useState<string | null>(null);
  const [devMode, setDevMode] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const yuan = formatYuan(amountCents);

  React.useEffect(() => {
    if (!open || !orderId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setCodeUrl(null);
    setDevMode(false);

    prepayPayOrder(orderId)
      .then((result) => {
        if (cancelled) return;
        if (result.mode === "dev") {
          setDevMode(true);
          return;
        }
        setCodeUrl(result.code_url ?? null);
        if (!result.code_url) {
          setError("未获取到支付二维码");
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setError(formatApiError(err, "发起支付失败"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, orderId]);

  React.useEffect(() => {
    if (!open || !orderId) return;

    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const order = await fetchPayOrder(orderId);
        if (cancelled || order.status !== "paid") return;
        window.clearInterval(timer);
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: queryKeys.tenantSubscription }),
          queryClient.invalidateQueries({ queryKey: ["billing", "orders"] }),
        ]);
        toast.success("支付成功");
        onOpenChange(false);
        await onPaid?.();
      } catch {
        // ignore polling errors
      }
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [open, orderId, onOpenChange, onPaid, queryClient]);

  async function handleSimulatePay() {
    if (!orderId) return;
    setSimulating(true);
    try {
      await simulatePayOrder(orderId);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.tenantSubscription }),
        queryClient.invalidateQueries({ queryKey: ["billing", "orders"] }),
      ]);
      toast.success("模拟支付成功");
      onOpenChange(false);
      await onPaid?.();
    } catch (err) {
      toast.error(formatApiError(err, "模拟支付失败"));
    } finally {
      setSimulating(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={loading || simulating}>
      <DialogContent className="max-w-md" aria-labelledby="pay-order-dialog-title">
        <DialogBody className="space-y-4 pb-5">
          <DialogHeader>
            <div className="min-w-0 flex-1 pr-2">
              <DialogTitle id="pay-order-dialog-title">{title}</DialogTitle>
              <DialogDescription>{description}</DialogDescription>
            </div>
            <DialogClose disabled={loading || simulating} />
          </DialogHeader>

          <div className="flex flex-col items-center gap-5">
            {loading ? (
              <div className="flex h-64 items-center justify-center">
                <Loader2 className="text-muted-foreground size-8 animate-spin" aria-hidden />
                <span className="sr-only">正在生成支付二维码</span>
              </div>
            ) : error ? (
              <p className="text-destructive text-center text-sm">{error}</p>
            ) : devMode ? (
              <div className="flex flex-col items-center gap-3 text-center">
                <p className="text-muted-foreground text-sm">
                  开发环境未配置微信支付，可使用模拟支付完成联调。
                </p>
                <Button type="button" disabled={simulating} onClick={handleSimulatePay}>
                  {simulating ? "处理中…" : "模拟支付成功"}
                </Button>
              </div>
            ) : codeUrl ? (
              <div className="rounded-xl border bg-white p-4">
                <QRCodeSVG value={codeUrl} size={240} level="M" includeMargin={false} />
              </div>
            ) : null}

            {!loading && !error ? (
              <p className="text-3xl font-semibold tabular-nums">¥{yuan}</p>
            ) : null}
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
