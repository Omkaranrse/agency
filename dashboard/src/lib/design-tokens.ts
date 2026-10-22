/**
 * Agency Design Tokens
 * Single source of truth for design tokens used across the Agency Dashboard.
 */

export const DESIGN_TOKENS = {
  colors: {
    light: {
      background: '#F8FAFC',
      surface: '#FFFFFF',
      border: '#E2E8F0',
      text: '#0F172A',
      mutedText: '#64748B',
      accent: '#0EA589',
      accentHover: '#0b8c74',
      accentSecondary: '#6366F1',
      success: '#10B981',
      warning: '#F59E0B',
      danger: '#EF4444',
      surfaceRaised: '#F1F5F9',
      focusRing: '#0EA589',
    },
    dark: {
      background: '#0A0D14',
      surface: '#121925',
      border: '#263244',
      text: '#F3F6FC',
      mutedText: '#A0AEC0',
      accent: '#40E0C0',
      accentHover: '#32c4a6',
      accentSecondary: '#8B8BFF',
      success: '#35D39A',
      warning: '#F6B756',
      danger: '#FF6B79',
      surfaceRaised: '#182231',
      focusRing: '#40E0C0',
    },
  },
  typography: {
    fontFamily: "'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    baseSize: '14px',
    scale: {
      xs: '0.75rem',    // 12px - badges, helper text
      sm: '0.875rem',   // 14px - base interface text, table cells, controls
      base: '1rem',     // 16px - subheadings, prominent descriptions
      lg: '1.125rem',   // 18px - card titles, section titles
      xl: '1.25rem',    // 20px - page subheadings
      '2xl': '1.5rem',  // 24px - page titles
    },
    weights: {
      regular: 400,
      medium: 500,
      semibold: 600,
    },
    lineHeights: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75,
    },
  },
  spacing: {
    sidebarWidth: '240px',
    headerHeight: '56px',
    pagePadding: '1.5rem',
    panelSpacing: '1rem',
  },
  radii: {
    default: '6px',
    sm: '4px',
    md: '6px',
    lg: '8px',
  },
  shadows: {
    subtle: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    popover: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  },
  transitions: {
    fast: '150ms ease-in-out',
    normal: '200ms ease-in-out',
  },
} as const;

export type RunStatus =
  | 'created'
  | 'planning'
  | 'awaiting_approval'
  | 'building'
  | 'testing'
  | 'deploying'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface StatusMeta {
  label: string;
  variant: 'neutral' | 'info' | 'warning' | 'success' | 'danger';
  description: string;
}

export const STATUS_DEFINITIONS: Record<RunStatus, StatusMeta> = {
  created: {
    label: 'Created',
    variant: 'neutral',
    description: 'Run has been initialized but not yet started.',
  },
  planning: {
    label: 'Planning',
    variant: 'info',
    description: 'Project Manager and Designer agents are formulating the site specification.',
  },
  awaiting_approval: {
    label: 'Awaiting Approval',
    variant: 'warning',
    description: 'Site specification and prototype await human operator approval.',
  },
  building: {
    label: 'Building',
    variant: 'info',
    description: 'Builder agent is generating Astro pages and code artifacts.',
  },
  testing: {
    label: 'Testing',
    variant: 'info',
    description: 'Automated QA service is validating build, links, and accessibility.',
  },
  deploying: {
    label: 'Deploying',
    variant: 'info',
    description: 'Deploying site artifacts to Cloudflare Pages.',
  },
  completed: {
    label: 'Completed',
    variant: 'success',
    description: 'Run finished successfully and preview is published.',
  },
  failed: {
    label: 'Failed',
    variant: 'danger',
    description: 'Run terminated due to an error.',
  },
  cancelled: {
    label: 'Cancelled',
    variant: 'neutral',
    description: 'Run was cancelled by an operator.',
  },
};
