import type { ComponentProps, ReactNode } from "react";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";

import { cn } from "@/lib/utils";

const linkBase =
  "inline-flex h-9 cursor-pointer items-center justify-center gap-1 whitespace-nowrap rounded-md text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-primary)]/40";

const linkGhost = "text-slate-500 hover:bg-slate-50 hover:text-slate-900";
const linkOutline =
  "border border-[color:var(--color-primary)] bg-[color:var(--color-primary)] text-white hover:bg-[color:var(--color-primary)] hover:text-white";

function Pagination({
  className,
  totalPages,
  ...props
}: ComponentProps<"nav"> & { totalPages?: number }) {
  if (totalPages !== undefined && totalPages <= 1) {
    return null;
  }

  return (
    <nav
      role="navigation"
      aria-label="分页"
      className={cn("mx-auto flex w-full justify-center", className)}
      {...props}
    />
  );
}

function PaginationContent({ className, ...props }: ComponentProps<"ul">) {
  return <ul className={cn("flex flex-row flex-wrap items-center gap-1", className)} {...props} />;
}

function PaginationItem({ className, ...props }: ComponentProps<"li">) {
  return <li className={cn("", className)} {...props} />;
}

type PaginationLinkProps = {
  isActive?: boolean;
  disabled?: boolean;
  size?: "icon" | "default";
  href?: string;
  onClick?: ComponentProps<"a">["onClick"];
  className?: string;
  children?: ReactNode;
} & Omit<ComponentProps<"a">, "href" | "onClick" | "className" | "children">;

function PaginationLink({
  className,
  isActive,
  disabled,
  size = "icon",
  href,
  onClick,
  children,
  ...props
}: PaginationLinkProps) {
  const classes = cn(
    linkBase,
    isActive ? linkOutline : linkGhost,
    size === "icon" ? "w-9" : "px-2.5",
    disabled && "pointer-events-none opacity-50",
    className,
  );

  if (href && !disabled) {
    return (
      <a
        href={href}
        aria-current={isActive ? "page" : undefined}
        className={classes}
        onClick={onClick}
        {...props}
      >
        {children}
      </a>
    );
  }

  return (
    <span
      aria-current={isActive ? "page" : undefined}
      aria-disabled={disabled || undefined}
      className={classes}
      {...props}
    >
      {children}
    </span>
  );
}

function PaginationPrevious({
  className,
  ...props
}: ComponentProps<typeof PaginationLink>) {
  return (
    <PaginationLink
      aria-label="上一页"
      size="default"
      className={cn("gap-1 px-2.5", className)}
      {...props}
    >
      <ChevronLeft className="size-4" aria-hidden />
      <span>上一页</span>
    </PaginationLink>
  );
}

function PaginationNext({
  className,
  ...props
}: ComponentProps<typeof PaginationLink>) {
  return (
    <PaginationLink
      aria-label="下一页"
      size="default"
      className={cn("gap-1 px-2.5", className)}
      {...props}
    >
      <span>下一页</span>
      <ChevronRight className="size-4" aria-hidden />
    </PaginationLink>
  );
}

function PaginationEllipsis({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      aria-hidden
      className={cn("flex size-9 items-center justify-center text-slate-500", className)}
      {...props}
    >
      <MoreHorizontal className="size-4" />
      <span className="sr-only">更多页</span>
    </span>
  );
}

export {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
};
