import {
  LayoutDashboard, Map, Smartphone, MessageSquare,
  Siren, FileCheck, LineChart, FolderOpen, Bell, TrendingUp,
  Users, Settings, Shield,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type NavItem = { to: string; label: string; icon: LucideIcon; roles?: string[] };

export const ALL_NAV: NavItem[] = [
  { to: '/', label: 'Safety Dashboard', icon: LayoutDashboard, roles: ['safety_officer', 'supervisor', 'admin'] },
  { to: '/heatmap', label: 'Geospatial Heatmap', icon: Map, roles: ['safety_officer', 'supervisor', 'permit_officer', 'compliance_officer', 'executive', 'admin'] },
  { to: '/incident', label: 'Incident Response', icon: Siren, roles: ['safety_officer', 'supervisor', 'admin'] },
  { to: '/permits', label: 'Permit Intelligence', icon: FileCheck, roles: ['permit_officer', 'safety_officer', 'admin'] },
  { to: '/copilot', label: 'AI Copilot', icon: MessageSquare, roles: ['safety_officer', 'supervisor', 'compliance_officer', 'executive', 'admin'] },
  { to: '/notifications', label: 'Notification Center', icon: Bell, roles: ['safety_officer', 'supervisor', 'permit_officer', 'compliance_officer', 'executive', 'admin'] },
  { to: '/analytics', label: 'Historical Analytics', icon: LineChart, roles: ['safety_officer', 'compliance_officer', 'executive', 'admin'] },
  { to: '/reports', label: 'Reports Library', icon: FolderOpen, roles: ['compliance_officer', 'safety_officer', 'executive', 'admin'] },
  { to: '/executive', label: 'Executive Dashboard', icon: TrendingUp, roles: ['executive', 'admin'] },
  { to: '/admin/users', label: 'User Management', icon: Users, roles: ['admin'] },
  { to: '/settings', label: 'Settings', icon: Settings, roles: ['admin', 'safety_officer'] },
  { to: '/mobile', label: 'Worker Mobile', icon: Smartphone, roles: ['worker', 'admin'] },
];

export function navForRole(role: string): NavItem[] {
  return ALL_NAV.filter((item) => !item.roles || item.roles.includes(role) || role === 'admin');
}

export function homeForRole(role: string): string {
  const map: Record<string, string> = {
    safety_officer: '/',
    permit_officer: '/permits',
    supervisor: '/',
    compliance_officer: '/reports',
    executive: '/executive',
    worker: '/mobile',
    admin: '/admin/users',
  };
  return map[role] || '/';
}
