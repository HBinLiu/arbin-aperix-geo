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
  useDialog,
} from "@/components/ui/dialog";
import type { PlanChangeConfirmCopy } from "@/lib/billing/plans";

type PlanChangeConfirmDialogProps = {
  open: boolean;
  copy: PlanChangeConfirmCopy | null;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
};

function PlanChangeConfirmFooter({
  confirmLabel,
  submitting,
  onConfirm,
}: {
  confirmLabel: string;
  submitting: boolean;
  onConfirm: () => void;
}) {
  const { requestClose } = useDialog();

  return (
    <DialogFooter>
      <Button type="button" variant="outline" disabled={submitting} onClick={requestClose}>
        取消
      </Button>
      <Button type="button" disabled={submitting} onClick={onConfirm}>
        {submitting ? "创建订单…" : confirmLabel}
      </Button>
    </DialogFooter>
  );
}

/** 升级 / 降级前确认（方案 1：全额支付，无退款）。 */
export function PlanChangeConfirmDialog({
  open,
  copy,
  submitting = false,
  onOpenChange,
  onConfirm,
}: PlanChangeConfirmDialogProps) {
  if (!copy) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-md" aria-labelledby="plan-change-confirm-title">
        <DialogBody className="space-y-4 pb-0">
          <DialogHeader>
            <div className="min-w-0 flex-1 pr-2">
              <DialogTitle id="plan-change-confirm-title">{copy.title}</DialogTitle>
              <DialogDescription className="sr-only">请确认套餐变更规则后再继续支付</DialogDescription>
            </div>
            <DialogClose disabled={submitting} />
          </DialogHeader>

          <ul className="text-muted-foreground list-disc space-y-2 pl-5 text-sm leading-relaxed">
            {copy.points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </DialogBody>

        <PlanChangeConfirmFooter
          confirmLabel={copy.confirmLabel}
          submitting={submitting}
          onConfirm={onConfirm}
        />
      </DialogContent>
    </Dialog>
  );
}
