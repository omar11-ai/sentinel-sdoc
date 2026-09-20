import { useEffect } from 'react'
import DashboardLayout from '../dashboard-layout'
import { DashboardPage } from '../components/tallie/dashboard-page'
import {
  DashboardNavigationProvider,
  useDashboardNavigation,
} from '../components/tallie/navigation'
import { ThemeProvider } from '../components/tallie/theme-provider'
import { TooltipProvider } from '@/components/ui/tooltip'
import { CinematicShell } from './cinematic/CinematicShell'
import { SentinelProvider, useSentinel } from './context'
import { SearchProvider } from './search'
import { LiquidGlassDefs } from '@/components/ui/apple-liquid-glass-switcher'

/* mirror the internal router state to the URL hash (deep-linkable views) */
function HashSync() {
  const { pathname, navigate } = useDashboardNavigation()
  useEffect(() => {
    const initial = window.location.hash.replace('#', '') || '/'
    if (initial !== pathname) navigate(initial)
    const onHash = () => navigate(window.location.hash.replace('#', '') || '/')
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    if (window.location.hash.replace('#', '') !== pathname) {
      window.history.replaceState(null, '', '#' + pathname)
    }
  }, [pathname])
  return null
}

function LoadingShell() {
  return (
    <div className="flex h-full items-center justify-center py-40">
      <p className="font-serif text-2xl text-muted-foreground">
        Pulling the current run…
      </p>
    </div>
  )
}

function ErrorShell({ message }: { message: string }) {
  return (
    <div className="flex h-full items-center justify-center py-40 px-6">
      <div className="flex max-w-md flex-col gap-2 rounded-xl border bg-zinc-50 p-6 dark:bg-muted">
        <p className="font-serif text-2xl">Backend unreachable</p>
        <p className="text-sm text-muted-foreground">{message}</p>
        <p className="text-xs text-muted-foreground">
          The FastAPI service (/api/health, /api/results) did not respond. On the
          live deployment this usually means Render free-tier cold start — retry
          in a few seconds.
        </p>
      </div>
    </div>
  )
}

function DashboardRoute() {
  const { error } = useSentinel()
  return (
    <div className="relative h-full">
      <CinematicShell />
      <div className="relative z-10 h-full">
        <DashboardLayout>
          {error ? <ErrorShell message={error} /> : <DashboardPage />}
        </DashboardLayout>
      </div>
    </div>
  )
}

export default function SentinelApp() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="sentinel-theme">
      <TooltipProvider delayDuration={0}>
      <SentinelProvider>
        <SearchProvider>
          <DashboardNavigationProvider>
            <HashSync />
            <LiquidGlassDefs />
            <DashboardRoute />
          </DashboardNavigationProvider>
        </SearchProvider>
      </SentinelProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}

export { LoadingShell }
