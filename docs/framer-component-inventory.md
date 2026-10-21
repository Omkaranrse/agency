# Framer Component Inventory & Interaction Architecture

This document records the component research, architectural mapping, licensing, and implementation strategies for the futuristic AI software agency command center, inspired by the free **Framer Marketplace** ([framer.com/marketplace/components/?pricing=free](https://www.framer.com/marketplace/components/?pricing=free)).

---

## 1. Inventory & Component Registry

| Component Name | Category | Marketplace Reference / Creator | Compatibility / Strategy | Intended Location | Implementation Details |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Glow Shimmer Button** | Buttons & Controls | *Framer Free Library / Andreas Storm* | Recreated (React + Framer Motion + CSS) | Global Actions, New Run, Approval Gate | Subtle gradient angle shimmer along border on hover, spring press scale (`0.98`), keyboard accessible. |
| **Tactile Magnetic Button** | Buttons & Controls | *Framer Marketplace / Benjamin den Boer* | Recreated (React + Framer Motion) | Quick Action toolbar, Run controls | Spring magnetic pull toward cursor within 20px threshold, haptic hover glow. |
| **Sliding Pill Segmented Control** | Tabs & Menus | *Framer Community / Edoardo Rainoldi* | Recreated (`layoutId` Framer Motion) | Route view toggles, Preview device switch | Smooth spring sliding pill indicator matching active tab dimensions. |
| **Command Shell Dock Sidebar** | Navigation & Shell | *Framer Marketplace / Matt Perry* | Ported & Recreated | `app-sidebar.tsx` | Collapsible width spring animation (64px to 240px), tooltips on collapsed state, active pill indicator. |
| **Matrix Grid & Scanline Background** | Background & Depth | *Framer Lab / KPR Verse* | Recreated (CSS Grid + Canvas/Motion) | Command Shell backdrop, Virtual Office | Subtle 24px matrix grid lines (`#273244` at 15% opacity) with restrained radial cursor spotlight. |
| **Rolling Number Ticker** | Metrics & Counters | *Framer Free / John Higgins* | Recreated (Framer Motion spring) | Runs Overview metrics, Task counters | Spring-interpolated numerical digits that roll into position when values update from SSE. |
| **Text Decrypt / Scramble Reveal** | Animated Typography | *Framer Marketplace / Paco Coursey* | Recreated (Custom React hook) | Agent status changes, stage milestones | Decrypts random glyphs into authoritative status text over 400ms on stage transitions. |
| **Pulse Radar Stage Node** | Workflow & Timeline | *Framer Free / Gavin Nelson* | Recreated (Framer Motion pulse) | Run Timeline, Workstation Cards | Concentric pulse rings on active running stages; glowing connecting data highways. |
| **Command Center Hologram Card** | Cards & Containers | *Framer Marketplace / Brian Lovin* | Recreated (Framer Motion + CSS) | Run Cards, Workstation Zones, Employee Roster | Depth border with `#273244` line, radial highlight on hover, restrained tilt effect. |
| **Audio Waveform Frequency Meter** | Voice & AI Manager | *Framer Audio / Studio Freight* | Recreated (Motion SVG Bars) | AI Manager voice panel, push-to-talk | 12 interactive sound wave bars that animate dynamically during microphone recording / TTS playback. |
| **Focus Glow Input Field** | Forms & Inputs | *Framer Forms / Tim Gabe* | Recreated (Tailwind + Framer Motion) | New Run brief form, Clarification inputs | High-contrast `#54E1C1` glow on focus, shake animation on validation error, inline helper tooltips. |
| **Spring Command Modal / Drawer** | Dialogs & Overlays | *Framer Overlay / Emil Kowalski* | Recreated (AnimatePresence) | Employee detail drawer, confirmation dialogs | Scale (`0.96` to `1.0`), smooth spring enter (`damping: 25`, `stiffness: 300`), backdrop blur. |
| **Live Heartbeat Pulse Pill** | Status & Indicators | *Framer Utility / Rasmus Andersson* | Recreated (Tailwind + CSS keyframes) | Top header, SSE stream status | Green/amber/red indicator with ping animation reflecting real WebSocket / SSE connection health. |

---

## 2. Implementation Approach & Licensing Rules

1. **Clean Code & Attribution**:
   - Rather than bundling opaque external binary bundles that cause hydration mismatches or SSR issues in Next.js App Router, all interaction patterns are ported or cleanly recreated as native, type-safe React 18 client components using `framer-motion` and Tailwind CSS.
   - All components adhere to strict TypeScript mode (`noImplicitAny`, exact types).
2. **Motion System Consistency**:
   - Shared motion tokens and easing curves are declared in `src/lib/motion.ts`.
   - Every component respects `prefers-reduced-motion` via `useReducedMotion()`.
3. **Zero Fabricated Metrics**:
   - Visual effects and rolling tickers are tied exclusively to authoritative backend events (`run.stage_changed`, domain metrics, task records). When data is unavailable, honest fallback states are displayed.
