/**
 * Navigation item definition — single source of truth for all sidebar routes.
 */
import {
  BrainCircuit,
  FileSearch2,
  FileText,
  FolderKanban,
  Home,
  NetworkIcon,
  Settings,
  Upload,
  UserCircle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  id: string
  label: string
  icon: LucideIcon
  path: string
  badge?: string | number
  section?: 'main' | 'tools' | 'account'
}

export const NAV_ITEMS: NavItem[] = [
  // ── Main ──
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: Home,
    path: '/app/dashboard',
    section: 'main',
  },
  {
    id: 'cases',
    label: 'Cases',
    icon: FolderKanban,
    path: '/app/cases',
    section: 'main',
  },
  {
    id: 'upload',
    label: 'Upload',
    icon: Upload,
    path: '/app/upload',
    section: 'main',
  },

  // ── Tools ──
  {
    id: 'knowledge-graph',
    label: 'Knowledge Graph',
    icon: NetworkIcon,
    path: '/app/knowledge-graph',
    section: 'tools',
  },
  {
    id: 'ai-assistant',
    label: 'AI Assistant',
    icon: BrainCircuit,
    path: '/app/ai-assistant',
    section: 'tools',
  },
  {
    id: 'evidence',
    label: 'Evidence',
    icon: FileSearch2,
    path: '/app/evidence',
    section: 'tools',
  },
  {
    id: 'reports',
    label: 'Reports',
    icon: FileText,
    path: '/app/reports',
    section: 'tools',
  },

  // ── Account ──
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    path: '/app/settings',
    section: 'account',
  },
  {
    id: 'profile',
    label: 'Profile',
    icon: UserCircle,
    path: '/app/profile',
    section: 'account',
  },
]

export const NAV_SECTIONS: { key: NavItem['section']; label: string }[] = [
  { key: 'main',    label: 'Workspace' },
  { key: 'tools',   label: 'Intelligence' },
  { key: 'account', label: 'Account' },
]
