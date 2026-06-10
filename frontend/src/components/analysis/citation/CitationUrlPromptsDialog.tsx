import { FaviconImage } from "@/components/common/FaviconImage";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import type { CitationUrlRow } from "@/types";

type CitationUrlPromptsDialogProps = {
  row: CitationUrlRow | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function CitationUrlPromptsDialog({
  row,
  open,
  onOpenChange,
}: CitationUrlPromptsDialogProps) {
  if (!row) return null;

  const displayHost = row.host || row.url;
  const title = row.title || row.url;
  const prompts = row.citing_prompts ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex max-w-xl flex-col"
        aria-labelledby="citation-url-prompts-dialog-title"
      >
        <div className="flex items-start justify-between px-6 pt-5 pb-8">
          <DialogTitle id="citation-url-prompts-dialog-title" className="text-lg">
            引用此页面的提示词
          </DialogTitle>
          <DialogClose />
        </div>

        <div className="flex min-w-0 items-center gap-2.5 px-6 pb-4">
          <FaviconImage
            domain={displayHost}
            pageUrl={row.url}
            size={20}
            className="size-5 shrink-0 rounded-sm"
          />
          <p className="min-w-0 truncate font-medium text-foreground">{title}</p>
        </div>

        <div className="border-border mx-6 mb-5 overflow-hidden rounded-lg border">
          {prompts.length === 0 ? (
            <p className="text-muted-foreground px-4 py-6 text-center text-sm">暂无引用此页面的提示词</p>
          ) : (
            <ul className="divide-border divide-y">
              {prompts.map((prompt, index) => (
                <li key={`${prompt.prompt_text}-${index}`} className="px-4 py-3">
                  <p className="font-medium text-foreground">{prompt.prompt_text}</p>
                  <p className="text-muted-foreground mt-1 text-sm">主题：{prompt.topic_name}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
