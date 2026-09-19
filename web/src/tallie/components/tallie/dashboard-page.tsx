import { useState } from 'react'
import { useSentinel, type EmailRecord } from '../../sentinel/context'
import { LoadingShell } from '../../sentinel/App'
import { EmailDetailsSheet } from '../../sentinel/EmailSheet'
import { ArchitecturePage, InboxPage, LabPage, OverviewPage, PipelinePage } from '../../sentinel/pages'
import { useDashboardNavigation } from './navigation'

export function DashboardPage() {
  const { pathname, navigate } = useDashboardNavigation()
  const { results, loading } = useSentinel()

  const [selected, setSelected] = useState<EmailRecord | null>(null)

  if (loading && !results) return <LoadingShell />

  const openEmail = (e: EmailRecord) => setSelected(e)

  let content: React.ReactNode
  switch (true) {
    case pathname === '/inbox' || pathname.startsWith('/inbox/'):
      content = <InboxPage onOpenEmail={openEmail} />
      break
    case pathname === '/pipeline':
      content = <PipelinePage />
      break
    case pathname === '/lab':
      content = <LabPage />
      break
    case pathname === '/architecture':
      content = <ArchitecturePage />
      break
    default:
      content = <OverviewPage onOpenEmail={openEmail} />
  }

  return (
    <>
      {content}
      <EmailDetailsSheet
        email={selected}
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelected(null)
            void navigate(pathname)
          }
        }}
      />
    </>
  )
}
