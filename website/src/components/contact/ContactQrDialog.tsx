import { X } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";

import { CONTACT_QR_IMAGE } from "@/lib/assets";

type ContactQrDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
};

/** 扫码联系弹窗（定价「联系销售」等入口共用）。 */
export function ContactQrDialog({
  open,
  onOpenChange,
  title = "联系销售",
  description = "微信扫码添加销售顾问",
}: ContactQrDialogProps) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onOpenChange(false);
    };
    window.addEventListener("keydown", onKeyDown);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prev;
    };
  }, [open, onOpenChange]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div className="contact-qr-root" role="presentation">
      <button
        type="button"
        className="contact-qr-backdrop"
        aria-label="关闭"
        onClick={() => onOpenChange(false)}
      />
      <div
        className="contact-qr-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="contact-qr-header">
          <h2 id={titleId} className="contact-qr-title">
            {title}
          </h2>
          <button
            type="button"
            className="contact-qr-close"
            aria-label="关闭"
            onClick={() => onOpenChange(false)}
          >
            <X size={20} aria-hidden />
          </button>
        </div>
        <div className="contact-qr-body">
          <img
            src={CONTACT_QR_IMAGE}
            alt={`${title}二维码`}
            width={220}
            height={220}
            className="contact-qr-image"
            decoding="async"
          />
          <p className="contact-qr-desc">{description}</p>
        </div>
      </div>
    </div>,
    document.body,
  );
}

type ContactQrButtonProps = {
  label?: string;
  title?: string;
  description?: string;
  className?: string;
};

/** 按钮 + 扫码弹窗；用于定价页「联系销售」。 */
export function ContactQrButton({
  label = "联系销售",
  title = "联系销售",
  description = "微信扫码添加销售顾问",
  className = "pricing-card-btn",
}: ContactQrButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button type="button" className={className} onClick={() => setOpen(true)}>
        {label}
      </button>
      <ContactQrDialog
        open={open}
        onOpenChange={setOpen}
        title={title}
        description={description}
      />
    </>
  );
}
