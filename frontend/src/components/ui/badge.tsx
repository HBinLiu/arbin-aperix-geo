import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  [
    "inline-flex w-fit shrink-0 items-center justify-center gap-1 whitespace-nowrap",
    "rounded-full border border-transparent px-2 py-1 text-xs font-medium",
    "[&>svg]:pointer-events-none [&>svg]:size-3",
  ].join(" "),
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground [a&]:hover:bg-primary/90",
        secondary:
          "bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90",
        destructive:
          "bg-destructive text-white dark:bg-destructive/60 [a&]:hover:bg-destructive/90",
        outline:
          "border-border bg-transparent text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
        ghost:
          "bg-transparent text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
        link: "bg-transparent text-primary underline-offset-4 [a&]:hover:underline",
        primary: "bg-primary/10 text-primary [a&]:hover:bg-primary/15",
        green: "bg-emerald-50 text-emerald-600 [a&]:hover:bg-emerald-100",
        red: "bg-red-50 text-red-600 [a&]:hover:bg-red-100",
        orange: "bg-orange-50 text-orange-600 [a&]:hover:bg-orange-100",
        muted: "bg-muted text-muted-foreground [a&]:hover:bg-muted/80",
        grayBlack: "bg-background text-foreground",
        success: "bg-success/10 text-success [a&]:hover:bg-success/15",
        error: "bg-error/10 text-error [a&]:hover:bg-error/15",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
