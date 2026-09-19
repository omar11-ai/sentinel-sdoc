import { useRef } from 'react'
import { motion, useInView, useReducedMotion } from 'motion/react'

/**
 * Hirael FeatureCard (original: features.tsx by MohammadShehadeh, MIT):
 * scale 0.95 -> 1 with stagger as it scrolls into view.
 */
const EASE_CARD: [number, number, number, number] = [0.22, 1, 0.36, 1]

export function FeatureCard({
  index,
  className,
  children,
}: {
  index: number
  className?: string
  children: React.ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  const reduce = useReducedMotion()
  const show = reduce || inView
  return (
    <motion.div
      ref={ref}
      initial={reduce ? false : { scale: 0.95, opacity: 0 }}
      animate={show ? { scale: 1, opacity: 1 } : undefined}
      transition={{ duration: 0.6, delay: (index % 4) * 0.12, ease: EASE_CARD }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
