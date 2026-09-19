import type { ComponentType } from 'react'
import {
  ArchiveIcon,
  BlocksIcon,
  FlaskConicalIcon,
  InboxIcon,
  LayoutGridIcon,
  RouteIcon,
} from 'lucide-react'

export type NavigationItem = {
  name: string
  href: string
  icon: ComponentType<{ className?: string }>
  badge?: string
}

export type NavigationGroup = {
  label: string
  items: NavigationItem[]
}

export const navigationGroups: NavigationGroup[] = [
  {
    label: 'Workspace',
    items: [
      { name: 'Overview', href: '/', icon: LayoutGridIcon },
      { name: 'Inbox', href: '/inbox', icon: InboxIcon, badge: '520' },
      { name: 'Pipeline', href: '/pipeline', icon: RouteIcon },
      { name: 'Generalize Lab', href: '/lab', icon: FlaskConicalIcon },
      { name: 'Architecture', href: '/architecture', icon: BlocksIcon },
    ],
  },
  {
    label: 'Verification',
    items: [
      { name: 'Mismatches', href: '/inbox/mismatch', icon: ArchiveIcon, badge: '46' },
    ],
  },
]

export const currentUser = {
  name: 'SENTINEL Desk',
  email: 'judges@sentinel-sdoc.onrender.com',
  avatar:
    'data:image/svg+xml;utf8,' +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0A1B39"/><path d="M9 22V10h14v3h-10v2.5h8v3h-8V22z" fill="#fff"/></svg>',
    ),
}

export const notifications = [
  {
    id: 'n1',
    title: '46 mismatches caught',
    description: 'container_count / gross_weight_kg / consignee diffs, evidence quoted per field.',
    time: 'current run',
  },
  {
    id: 'n2',
    title: '20 cases escalated to a human',
    description: '4 canonical reasons — the system refuses to guess.',
    time: 'current run',
  },
  {
    id: 'n3',
    title: 'Official self-check: 1.0',
    description: 'macro F1 1.0 · defect F1 1.0 · E2E 46/46 · escalation F1 1.0.',
    time: 'scoreboard_v10',
  },
]
