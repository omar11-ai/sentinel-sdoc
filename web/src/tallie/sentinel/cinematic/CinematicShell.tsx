import { useTheme } from '../../components/tallie/theme-provider'
import { CinematicBackground, NoiseOverlay } from './primitives'

/**
 * The Hirael cinematic backdrop, mounted behind the dashboard content in
 * dark mode: slowly drifting blurred warm gradients + film grain + vignette.
 * Primitives are the original MIT-licensed ones from
 * MohammadShehadeh/hirael (templates/creative-studio).
 */
export function CinematicShell() {
  const { resolvedTheme } = useTheme()
  if (resolvedTheme !== 'dark') return null
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <CinematicBackground variant="hero" />
      <NoiseOverlay variant="bg" className="opacity-[0.12]" />
    </div>
  )
}
