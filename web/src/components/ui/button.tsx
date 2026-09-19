import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"
import { glassButtonClasses } from "@/components/ui/glass-button"

/**
 * Every variant shares the liquid-glass pill treatment (glassButtonClasses):
 * translucent fill + backdrop blur + top specular edge + hover lift.
 * Variants only tint the glass. tailwind-merge keeps the last conflicting
 * class, so variant classes cleanly override the shared glass fill.
 */
const buttonVariants = cva(
  cn(
    glassButtonClasses,
    "focus-visible:border-ring aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:aria-invalid:border-destructive/50 aria-invalid:ring-3",
    "text-sm font-medium inline-flex items-center justify-center whitespace-nowrap shrink-0 group/button select-none",
  ),
  {
    variants: {
      variant: {
        default:
          "bg-primary/90 text-primary-foreground dark:bg-primary dark:text-background border-transparent shadow-[inset_0_1px_0_0_rgba(255,255,255,0.45),0_2px_8px_rgba(0,0,0,0.12)] backdrop-blur-md hover:bg-primary dark:hover:bg-primary hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.55),0_6px_16px_rgba(0,0,0,0.18)] [a]:hover:bg-primary",
        outline:
          "aria-expanded:bg-white/60 dark:aria-expanded:bg-white/[0.11] aria-expanded:text-foreground",
        secondary:
          "bg-secondary/60 dark:bg-white/[0.09] hover:bg-secondary/80 dark:hover:bg-white/[0.14] aria-expanded:bg-secondary/80 dark:aria-expanded:bg-white/[0.14] aria-expanded:text-foreground",
        ghost:
          "border-transparent bg-transparent shadow-none dark:bg-transparent backdrop-blur-none hover:bg-white/45 hover:border-black/10 hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.6)] dark:hover:bg-white/[0.08] dark:hover:border-white/15 dark:hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.14)] hover:-translate-y-px aria-expanded:bg-white/45 dark:aria-expanded:bg-white/[0.08] aria-expanded:text-foreground active:translate-y-0",
        destructive:
          "border-destructive/25 bg-destructive/10 text-destructive backdrop-blur-md hover:bg-destructive/20 dark:bg-destructive/15 dark:hover:bg-destructive/25 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40",
        link: "border-transparent bg-transparent shadow-none backdrop-blur-none dark:bg-transparent text-primary underline-offset-4 hover:underline hover:bg-transparent hover:translate-y-0 hover:shadow-none dark:hover:bg-transparent rounded-lg",
      },
      size: {
        default: "h-8 gap-1.5 px-3 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-6 gap-1 px-2 text-xs [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1 px-2.5 text-[0.8rem] [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 gap-1.5 px-3.5 has-data-[icon=inline-end]:pr-3 has-data-[icon=inline-start]:pl-3",
        icon: "size-8",
        "icon-xs": "size-6 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-7 [&_svg:not([class*='size-'])]:size-3.5",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
