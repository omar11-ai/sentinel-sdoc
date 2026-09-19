import { motion, useReducedMotion } from 'motion/react'
import { useTheme } from '../../components/tallie/theme-provider'

/**
 * Ambient backdrop for BOTH themes, Hirael-style: slowly drifting blurred
 * gradients + film-grain + (dark only) vignette. Light = warm paper, dark =
 * cinematic black. Content sits above it; glass panels blur it (liquid glass).
 */
const DARK_GRADIENT =
  'radial-gradient(45% 45% at 28% 30%, rgba(222,219,200,0.14), transparent 70%),' +
  'radial-gradient(42% 42% at 73% 62%, rgba(196,162,120,0.18), transparent 72%),' +
  'radial-gradient(70% 55% at 50% 112%, rgba(36,30,22,0.9), transparent 72%),' +
  '#070707'

const LIGHT_GRADIENT =
  'radial-gradient(45% 45% at 28% 30%, rgba(216,209,190,0.5), transparent 70%),' +
  'radial-gradient(42% 42% at 73% 62%, rgba(201,182,150,0.35), transparent 72%),' +
  'radial-gradient(70% 55% at 50% 112%, rgba(255,255,255,0.95), transparent 72%),' +
  '#faf9f6'

const noiseUri = (dark: boolean) => {
  const c = dark ? '1' : '0'
  const a = dark ? '0.5' : '0.32'
  const svg =
    `<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>` +
    `<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/>` +
    `<feColorMatrix values='0 0 0 0 ${c} 0 0 0 0 ${c} 0 0 0 0 ${c} 0 0 0 ${a} 0'/></filter>` +
    `<rect width='100%' height='100%' filter='url(#n)'/></svg>`
  return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`
}

const VIGNETTE = 'radial-gradient(125% 120% at 50% 0%, transparent 52%, rgba(0,0,0,0.5) 100%)'

export function CinematicShell() {
  const { resolvedTheme } = useTheme()
  const dark = resolvedTheme === 'dark'
  const reduce = useReducedMotion()
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <motion.div
        className="absolute -inset-1/3"
        style={{ background: dark ? DARK_GRADIENT : LIGHT_GRADIENT, filter: 'blur(40px)' }}
        animate={
          reduce
            ? undefined
            : { x: ['-3%', '3%', '-3%'], y: ['-2%', '2%', '-2%'], rotate: [0, 6, 0], scale: [1, 1.12, 1] }
        }
        transition={{ duration: 34, repeat: Infinity, repeatType: 'mirror', ease: 'easeInOut' }}
      />
      <div
        className="absolute inset-0"
        style={{ backgroundImage: noiseUri(dark), backgroundSize: '160px 160px', opacity: dark ? 0.5 : 0.55 }}
      />
      {dark ? <div className="absolute inset-0" style={{ background: VIGNETTE }} /> : null}
    </div>
  )
}
