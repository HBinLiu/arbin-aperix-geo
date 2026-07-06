import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type KnowledgeInputDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  text: string;
  onTitleChange: (value: string) => void;
  onTextChange: (value: string) => void;
  onSubmit: () => void;
  submitting?: boolean;
  mode?: "create" | "edit";
};

export function KnowledgeInputDialog({
  open,
  onOpenChange,
  title,
  text,
  onTitleChange,
  onTextChange,
  onSubmit,
  submitting = false,
  mode = "create",
}: KnowledgeInputDialogProps) {
  const canSubmit = text.trim().length > 0 && !submitting;

  return (
    <Dialog open={open} onOpenChange={onOpenChange} closeDisabled={submitting}>
      <DialogContent className="max-w-xl">
        <DialogBody className="space-y-4 pb-0">
          <DialogHeader className="flex-col items-start">
            <DialogTitle>{mode === "edit" ? "编辑内容" : "录入内容"}</DialogTitle>
            <DialogDescription>
              录入的内容将作为向量化索引的重要文本来源。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-1.5">
            <label htmlFor="knowledge-input-title" className="text-foreground text-sm font-medium">
              标题
            </label>
            <Input
              id="knowledge-input-title"
              value={title}
              onChange={(event) => onTitleChange(event.target.value)}
              placeholder="品牌介绍"
              disabled={submitting}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="knowledge-input-text" className="text-foreground text-sm font-medium">
              正文
            </label>
            <textarea
              id="knowledge-input-text"
              value={text}
              onChange={(event) => onTextChange(event.target.value)}
              placeholder="填写品牌定位、核心业务、目标客群与差异化优势等。"
              rows={8}
              disabled={submitting}
              className={cn(
                "border-input placeholder:text-muted-foreground focus-visible:border-primary focus-visible:ring-primary/30 w-full resize-y rounded-md border bg-muted-background px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px]",
                "disabled:cursor-not-allowed disabled:opacity-50",
              )}
            />
          </div>
        </DialogBody>

        <DialogFooter>
          <Button type="button" variant="outline" disabled={submitting} onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button type="button" disabled={!canSubmit} onClick={onSubmit}>
            {submitting ? <Loader2 className="mr-2 size-4 animate-spin" aria-hidden /> : null}
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
