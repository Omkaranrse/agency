# Agency Dashboard — Phase 12

This directory contains the Next.js operator dashboard and reusable design system for **Agency**, an internal AI software agency management platform.

## Architecture

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (Strict Mode)
- **Styling**: Tailwind CSS + shadcn/ui primitives (`@radix-ui`)
- **Typography**: Poppins (weights 400, 500, 600) via `next/font/google`
- **Design Tokens**: Strict CSS custom properties in `src/app/globals.css`
- **Component Primitives**: Accessible, typed UI components in `src/components/ui/`
- **Application Shell**: Responsive sidebar, breadcrumb header, and layout in `src/components/layout/`

## Visual & Aesthetic Direction

Built as a clean, understated, professional internal operations tool.

Strict visual constraints enforced:
- No gradients
- No glassmorphism or backdrop blur
- No neon or glowing elements
- No oversized marketing typography
- No decorative illustrations or emoji icons
- No unnecessary animations
- Subtle borders, restrained spacing, clear typography, and 6px default radius

## Design Tokens

### Light Theme
| Token | Hex Value | Role |
|---|---|---|
| Background | `#F7F6F3` | Page background |
| Surface | `#FFFFFF` | Cards, panels, tables |
| Border | `#E4E1DA` | Container and divider borders |
| Text | `#1F2328` | Primary interface typography |
| Muted text | `#6B7280` | Secondary descriptions and metadata |
| Accent | `#2C5F5A` | Primary brand accent and focus rings |
| Success | `#3D7A4F` | Completed runs and success badges |
| Warning | `#B7791F` | Awaiting approval and alerts |
| Danger | `#B4443C` | Failed runs and destructive actions |

### Dark Theme
| Token | Hex Value | Role |
|---|---|---|
| Background | `#16181D` | Near-black page background |
| Surface | `#1F242C` | Raised surface and panels |
| Border | `#2E3440` | Subtle dark borders |
| Text | `#ECEFF4` | High-contrast readable typography |
| Muted text | `#9CA3AF` | Accessible secondary text |
| Accent | `#4C8B82` | Desaturated teal accent |
| Success | `#4E9A66` | Muted green status |
| Warning | `#D08770` | Warm amber status |
| Danger | `#BF616A` | Muted red status |

## Routes

- `/runs`: Run orchestration list foundation (Phase 12 empty state; real telemetry in Phase 13).
- `/new-run`: Client website brief submission form with client-side validation.
- `/settings`: Appearance mode (Light/Dark/System) and interface density preferences.
- `/design`: Comprehensive design system showcase exhibiting all tokens, badges, buttons, inputs, data tables, dialogs, and skeletons.

## Verification

```bash
pnpm run typecheck   # TypeScript strict check (tsc --noEmit)
pnpm run lint        # Next.js ESLint
pnpm run build       # Production Next.js build
```
