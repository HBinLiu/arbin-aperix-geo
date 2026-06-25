import * as React from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

const DIALOG_EXIT_MS = 200;

type DialogContextValue = {
  closing: boolean;
  requestClose: () => void;
  closeDisabled: boolean;
};

const DialogContext = React.createContext<DialogContextValue | null>(null);

function useDialogContext(): DialogContextValue {
  const context = React.useContext(DialogContext);
  if (!context) {
    throw new Error("Dialog components must be used within Dialog");
  }
  return context;
}

/** 对话框关闭控制（取消按钮等） */
export function useDialog(): DialogContextValue {
  return useDialogContext();
}

type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  closeDisabled?: boolean;
  children: React.ReactNode;
};

function Dialog({ open, onOpenChange, closeDisabled = false, children }: DialogProps) {
  const [present, setPresent] = React.useState(open);
  const [closing, setClosing] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setPresent(true);
      setClosing(false);
      return;
    }
    if (!present) return;
    setClosing(true);
    const timer = window.setTimeout(() => {
      setPresent(false);
      setClosing(false);
    }, DIALOG_EXIT_MS);
    return () => window.clearTimeout(timer);
  }, [open, present]);

  const requestClose = React.useCallback(() => {
    if (!closeDisabled) onOpenChange(false);
  }, [closeDisabled, onOpenChange]);

  React.useEffect(() => {
    if (!present || closing) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") requestClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [present, closing, requestClose]);

  if (!present) return null;

  const node = (
    <DialogContext.Provider value={{ closing, requestClose, closeDisabled }}>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">{children}</div>
    </DialogContext.Provider>
  );

  return typeof document !== "undefined" ? createPortal(node, document.body) : node;
}

function DialogOverlay({ className, ...props }: React.ComponentProps<"button">) {
  const { closing, requestClose } = useDialogContext();

  return (
    <button
      type="button"
      aria-label="关闭对话框"
      className={cn(
        "absolute inset-0 bg-black/80 backdrop-blur-sm",
        closing ? "animate-out fade-out-0 duration-200" : "animate-in fade-in-0 duration-200",
        className,
      )}
      onClick={requestClose}
      {...props}
    />
  );
}

type DialogContentProps = React.ComponentProps<"div">;

function DialogContent({ className, children, ...props }: DialogContentProps) {
  const { closing } = useDialogContext();

  return (
    <>
      <DialogOverlay />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          "border-border relative z-10 w-full rounded-xl border bg-white shadow-lg",
          closing
            ? "animate-out fade-out-0 zoom-out-95 duration-200"
            : "animate-in fade-in-0 zoom-in-95 duration-200",
          className,
        )}
        onClick={(event) => event.stopPropagation()}
        {...props}
      >
        {children}
      </div>
    </>
  );
}

function DialogClose({ className, disabled, ...props }: React.ComponentProps<"button">) {
  const { requestClose, closeDisabled } = useDialogContext();

  return (
    <button
      type="button"
      aria-label="关闭"
      className={cn("text-muted-foreground hover:text-foreground -mr-1 rounded-md p-1", className)}
      disabled={disabled ?? closeDisabled}
      onClick={requestClose}
      {...props}
    >
      <X className="size-5" aria-hidden />
    </button>
  );
}

function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("flex items-start justify-between", className)} {...props} />;
}

function DialogTitle({ className, ...props }: React.ComponentProps<"h2">) {
  return <h2 className={cn("text-base font-semibold", className)} {...props} />;
}

function DialogDescription({ className, ...props }: React.ComponentProps<"p">) {
  return <p className={cn("text-muted-foreground mt-2 text-sm leading-relaxed", className)} {...props} />;
}

function DialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("p-5", className)} {...props} />;
}

function DialogFooter({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("flex justify-end gap-2 px-5 py-4", className)} {...props} />;
}

export {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogTitle,
};
