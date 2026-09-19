'use client';

import * as React from 'react';
import { Slot } from 'radix-ui';
import { cn } from '@/lib/utils';

/**
 * GlassButton — liquid-glass pill button.
 *
 * The shared glass treatment lives in `glassButtonClasses` so the standard
 * Button's `outline` variant can reuse the exact same look. Structure:
 * a translucent, backdrop-blurred pill with a top specular edge, a soft
 * inner drop and a gentle lift on hover — in both themes.
 */

export const glassButtonClasses = cn(
  'relative overflow-hidden rounded-full',
  'border border-black/10 dark:border-white/15',
  'bg-white/45 dark:bg-white/[0.07]',
  'backdrop-blur-xl backdrop-saturate-150',
  'text-foreground',
  'shadow-[inset_0_1px_0_0_rgba(255,255,255,0.65),inset_0_-1px_0_0_rgba(0,0,0,0.05),0_1px_2px_rgba(0,0,0,0.06)]',
  'dark:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.16),inset_0_-1px_0_0_rgba(0,0,0,0.28),0_2px_6px_rgba(0,0,0,0.35)]',
  'transition-[transform,background-color,border-color,box-shadow] duration-200 ease-out',
  'hover:-translate-y-px hover:bg-white/60 dark:hover:bg-white/[0.11] hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.75),0_4px_12px_rgba(0,0,0,0.10)]',
  'dark:hover:shadow-[inset_0_1px_0_0_rgba(255,255,255,0.22),0_6px_18px_rgba(0,0,0,0.45)]',
  'active:translate-y-0 active:scale-[0.97]',
  'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-(--live)/50',
  'disabled:pointer-events-none disabled:opacity-60',
  '[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*="size-"])]:size-4',
);

const SIZE = {
  sm: 'h-9 gap-1.5 px-4 text-[13px]',
  default: 'h-10 gap-2 px-5 text-sm',
  lg: 'h-12 gap-2 px-7 text-base',
  icon: 'size-10 [&_svg:not([class*="size-"])]:size-5',
} as const;

export interface GlassButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: keyof typeof SIZE
  asChild?: boolean
}

export function GlassButton({
  size = 'default',
  asChild = false,
  className,
  children,
  type = 'button',
  ...props
}: GlassButtonProps) {
  const Comp: React.ElementType = asChild ? Slot.Root : 'button'
  return (
    <Comp
      data-slot="glass-button"
      className={cn(glassButtonClasses, SIZE[size], className)}
      {...(asChild ? {} : { type })}
      {...props}
    >
      {children}
    </Comp>
  );
}
