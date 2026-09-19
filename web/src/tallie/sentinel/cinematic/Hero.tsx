import { ArrowRight } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'

import { WordsPullUp, WordsPullUpMultiStyle, ScrollRevealText } from './primitives'

/**
 * Hirael hero grammar (original template: hero.tsx by MohammadShehadeh, MIT):
 * giant pull-up wordmark with asterisk, fade-up paragraph, pill CTA whose
 * circular chip scales and whose gap widens on hover.
 */
const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1]

export function CinematicHero({ onOpenInbox }: { onOpenInbox: () => void }) {
  const reduce = useReducedMotion()
  const fade = (delay: number) => ({
    initial: reduce ? false : ({ y: 20, opacity: 0 } as const),
    animate: { y: 0, opacity: 1 },
    transition: { duration: 0.8, delay, ease: EASE_OUT_EXPO },
  })

  return (
    <div className="relative flex flex-col gap-6 overflow-hidden rounded-2xl border border-(--border) bg-[#0b0a09] px-5 pt-20 pb-6 md:rounded-[2rem] md:px-8 md:pt-28 md:pb-8">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60" />
      <div className="relative z-10 flex flex-col gap-1">
        <motion.p
          {...fade(0.15)}
          className="text-[10px] font-medium tracking-[0.24em] text-[#dedbc8]/80 uppercase sm:text-xs"
        >
          SI ⇄ BL verification — human in the loop
        </motion.p>
        <h1 className="font-serif text-[17vw] leading-[0.85] font-medium tracking-[-0.05em] text-(--cs-cream) sm:text-[13vw] lg:text-[8.5rem]">
          <WordsPullUp text="Sentinel" showAsterisk />
        </h1>
      </div>

      <div className="relative z-10 grid grid-cols-12 items-end gap-6">
        <motion.p
          {...fade(0.5)}
          className="col-span-12 max-w-md text-sm text-(--cs-muted) sm:text-base lg:col-span-8"
          style={{ lineHeight: 1.35 }}
        >
          It reads every email in the shipping inbox, checks every field of the
          documents, quotes the evidence line by line — and when something can
          not be proven, it refuses to guess and calls a human.
        </motion.p>
        <motion.div {...fade(0.7)} className="col-span-12 flex flex-col gap-4 lg:col-span-4">
          <button
            type="button"
            onClick={onOpenInbox}
            className="group inline-flex w-fit cursor-pointer items-center gap-2 rounded-full bg-(--cs-cream) py-1.5 ps-5 pe-1.5 text-sm font-medium text-(--cs-ink) transition-all duration-300 hover:gap-3 sm:text-base"
          >
            Open the inbox
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-(--cs-ink) transition-transform duration-300 group-hover:scale-110 sm:h-10 sm:w-10">
              <ArrowRight className="h-4 w-4 -rotate-45 text-(--cs-cream)" />
            </span>
          </button>
        </motion.div>
      </div>
    </div>
  )
}

/**
 * Hirael about-panel grammar (original: about.tsx): rounded 2rem black panel,
 * eyebrow, mixed-style pull-up heading with an Instrument-Serif-italic
 * segment, and scroll-linked letter reveal for the body.
 */
export function CinematicAbout() {
  return (
    <div className="flex flex-col items-center gap-10 rounded-[2rem] bg-[#101010] px-6 py-14 text-center sm:px-10 sm:py-16 md:px-16 md:py-20">
      <span className="text-[10px] font-medium tracking-[0.24em] text-[#dedbc8] uppercase sm:text-xs">
        46 defects caught · 20 escalations · 0 guesses
      </span>
      <h2
        className="mx-auto max-w-3xl text-3xl leading-[1.02] sm:text-4xl md:text-5xl"
        style={{ color: '#e1e0cc' }}
      >
        <WordsPullUpMultiStyle
          segments={[
            { text: 'Every verdict ships with its evidence,', className: 'font-normal' },
            { text: 'quoted from the source line.', className: 'italic [font-family:var(--font-serif)]' },
          ]}
        />
      </h2>
      <ScrollRevealText
        text="The official scorer agrees: classification macro F1 1.0, defect F1 1.0, 46 of 46 end-to-end, and every one of the twenty escalations correct — five out of five per canonical reason. Press Re-decide with AI on any email and watch the live model reach the same verdict."
        className="mx-auto max-w-2xl text-xs leading-relaxed text-[#dedbc8] sm:text-sm md:text-base"
      />
    </div>
  )
}
