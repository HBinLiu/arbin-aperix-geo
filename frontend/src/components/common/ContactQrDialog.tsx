import {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CONTACT_QR_IMAGE } from "@/lib/assets/shell";

type ContactQrDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
};

/** 扫码联系弹窗（客服 / 联系我们 / 联系销售共用同一二维码）。 */
export function ContactQrDialog({
  open,
  onOpenChange,
  title = "联系我们",
  description = "微信扫码添加，我们会尽快与你联系",
}: ContactQrDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xs">
        <DialogBody className="space-y-4 pb-5">
          <DialogHeader>
            <div className="min-w-0 flex-1 pr-2">
              <DialogTitle>{title}</DialogTitle>
            </div>
            <DialogClose />
          </DialogHeader>
          <div className="flex flex-col items-center gap-3">
            <img
              src={CONTACT_QR_IMAGE}
              alt={`${title}二维码`}
              width={220}
              height={220}
              className="size-[220px] rounded-lg bg-white object-contain p-2"
              decoding="async"
            />
            <DialogDescription className="mt-0 text-center">{description}</DialogDescription>
          </div>
        </DialogBody>
      </DialogContent>
    </Dialog>
  );
}
