import {
  Children,
  Fragment,
  cloneElement,
  createElement,
  isValidElement,
  useMemo,
  type ReactNode,
} from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { TextBadge } from "@/components/ui/badge";
import {
  resolveMentionCanonicalLabel,
  resolveMentionIconLabel,
  splitTextByTerms,
  type ResponseMentionTerm,
} from "@/lib/analysis/responseDetail";
import { cn } from "@/lib/utils";

type ReplyMarkdownContentProps = {
  text: string;
  mentionTerms: ResponseMentionTerm[];
  className?: string;
};

function BrandInlineChip({ label, iconLabel }: { label: string; iconLabel: string }) {
  return (
    <TextBadge
      variant="primary"
      className="mx-0.5 inline-flex h-auto items-center gap-1 rounded-md px-1 py-0.5 align-baseline"
    >
      <BrandRankIcon label={iconLabel} size="xs" />
      <span className="text-xs font-medium">{label}</span>
    </TextBadge>
  );
}

function renderMentionText(text: string, mentionTerms: ResponseMentionTerm[]): ReactNode {
  const terms = mentionTerms.map((item) => item.term);
  const segments = splitTextByTerms(text, terms);

  return segments.map((segment, index) => {
    if (segment.type === "term") {
      return (
        <BrandInlineChip
          key={`mention-${index}`}
          label={resolveMentionCanonicalLabel(segment.value, mentionTerms)}
          iconLabel={resolveMentionIconLabel(segment.value, mentionTerms)}
        />
      );
    }
    return <Fragment key={`text-${index}`}>{segment.value}</Fragment>;
  });
}

function withMentions(children: ReactNode, mentionTerms: ResponseMentionTerm[]): ReactNode {
  if (children == null || typeof children === "boolean") return children;
  if (typeof children === "string") return renderMentionText(children, mentionTerms);
  if (typeof children === "number") return String(children);

  if (Array.isArray(children)) {
    return Children.map(children, (child, index) => (
      <Fragment key={index}>{withMentions(child, mentionTerms)}</Fragment>
    ));
  }

  if (isValidElement(children)) {
    if (children.type === "code" || children.type === "pre") {
      return children;
    }
    const childChildren = children.props.children;
    if (childChildren != null) {
      return cloneElement(children, children.props, withMentions(childChildren, mentionTerms));
    }
  }

  return children;
}

function buildMarkdownComponents(mentionTerms: ResponseMentionTerm[]): Components {
  const wrap = <T extends keyof JSX.IntrinsicElements>(Tag: T, className?: string) =>
    ({ children, node: _node, ...props }: React.ComponentPropsWithoutRef<T> & { node?: unknown }) =>
      createElement(Tag, { ...props, className }, withMentions(children, mentionTerms));

  return {
    h1: wrap("h1", "text-muted-foreground mt-4 mb-3 text-lg font-semibold first:mt-0"),
    h2: wrap("h2", "text-muted-foreground mt-4 mb-3 text-base font-semibold first:mt-0"),
    h3: wrap("h3", "text-muted-foreground mt-3 mb-2 text-sm font-semibold first:mt-0"),
    h4: wrap("h4", "text-muted-foreground mt-3 mb-2 text-sm font-semibold first:mt-0"),
    p: wrap("p", "mb-3 last:mb-0"),
    ul: wrap("ul", "mb-3 list-disc space-y-1 pl-5 last:mb-0"),
    ol: wrap("ol", "mb-3 list-decimal space-y-1 pl-5 last:mb-0"),
    li: wrap("li", "leading-7"),
    blockquote: wrap(
      "blockquote",
      "border-border text-muted-foreground mb-3 border-l-2 pl-4 last:mb-0",
    ),
    strong: wrap("strong", "text-muted-foreground font-semibold"),
    em: wrap("em", "italic"),
    hr: ({ node: _node, ...props }) => (
      <hr className="border-border my-4" {...props} />
    ),
    a: ({ href, children, node: _node, ...props }) => (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="text-muted-foreground underline underline-offset-2"
        {...props}
      >
        {withMentions(children, mentionTerms)}
      </a>
    ),
    code: ({ className, children, node: _node, ...props }) => {
      const isBlock = Boolean(className?.includes("language-"));
      return (
        <code
          className={cn(
            isBlock
              ? "block text-[0.9em]"
              : "bg-muted rounded px-1 py-0.5 text-[0.9em]",
            className,
          )}
          {...props}
        >
          {children}
        </code>
      );
    },
    pre: ({ children, node: _node, ...props }) => (
      <pre
        className="bg-muted text-muted-foreground mb-3 overflow-x-auto rounded-lg p-3 text-sm last:mb-0"
        {...props}
      >
        {children}
      </pre>
    ),
    table: ({ children, node: _node, ...props }) => (
      <div className="mb-3 overflow-x-auto last:mb-0">
        <table className="border-border w-full border text-sm" {...props}>
          {children}
        </table>
      </div>
    ),
    thead: wrap("thead", "bg-muted/50"),
    th: wrap("th", "border-border border px-3 py-2 text-left font-semibold"),
    td: wrap("td", "border-border border px-3 py-2 align-top"),
  };
}

/** AI 回复 Markdown 正文，含提及品牌主色 Badge */
export function ReplyMarkdownContent({ text, mentionTerms, className }: ReplyMarkdownContentProps) {
  const components = useMemo(
    () => buildMarkdownComponents(mentionTerms),
    [mentionTerms],
  );

  return (
    <div className={cn("text-muted-foreground text-left text-sm leading-7", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
