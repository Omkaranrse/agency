# Agency Reusable Portfolio Template (`site-astro`)

A production-ready, accessible, multi-page portfolio website template built with **Astro 4**, **Tailwind CSS**, **TypeScript (Strict Mode)**, and centralized **CSS Design Tokens**.

This template is designed to be copied into an isolated sandbox and customized programmatically by Agency AI agents or human developers without altering component internals.

---

## 1. Supported Use Cases

- **Developer & Architect Portfolios**: Highlighting systems architecture, technical case studies, and engineering timelines.
- **Agency Client Prototypes**: Rapidly generated initial prototypes derived from client briefs.
- **Accessible Multi-Page Marketing Sites**: Fast, static sites requiring WCAG 2.2 AA conformance and clean typography.

---

## 2. Prerequisites & Supported Runtime Versions

- **Node.js**: `v20.x` (Tested and built with Node.js `v20.20.1` and `v20.18.0`).
- **pnpm**: `v10.x` or `v9.x` (`pnpm-lock.yaml` is committed).
- **Astro**: `v4.16.x`.
- **Operating System**: macOS, Linux, or Windows.

---

## 3. Quick Start

### Installation

```bash
cd templates/site-astro
pnpm install
```

### Development Server

Starts the local development server at `http://localhost:4321`:

```bash
pnpm dev
```

### Production Build

Typechecks with `@astrojs/check` and generates static HTML/CSS in `dist/`:

```bash
pnpm build
```

### Preview Server

Serves the built production static artifacts locally:

```bash
pnpm preview
```

---

## 4. Directory Structure

```text
templates/site-astro/
├── README.md                  # This documentation
├── package.json               # Scripts and pinned dependencies
├── pnpm-lock.yaml             # Committed dependency lockfile
├── astro.config.mjs           # Astro SSG and Tailwind integration
├── tailwind.config.mjs        # Tailwind mapping to CSS design tokens
├── tsconfig.json              # Strict TypeScript configuration
├── .gitignore                 # Build and environment ignore patterns
├── public/
│   ├── favicon.svg            # Accessible brand favicon
│   └── images/                # Vector SVG illustrations for projects
├── src/
│   ├── content/
│   │   ├── config.ts          # Zod validation schemas and TypeScript types
│   │   ├── site.json          # Global site metadata, navigation, and SEO
│   │   ├── home.json          # Hero, highlights, and CTA copy
│   │   ├── about.json         # Bio, competencies, and career timeline
│   │   ├── projects.json      # Structured project case studies and tags
│   │   └── contact.json       # Inquiry headers, email, and form mode
│   ├── layouts/
│   │   └── BaseLayout.astro   # Semantic HTML shell, SEO, skip link, tokens
│   ├── pages/
│   │   ├── index.astro        # Home page route (/)
│   │   ├── about.astro        # About page route (/about)
│   │   ├── projects.astro     # Projects listing route (/projects)
│   │   └── contact.astro      # Contact page route (/contact)
│   ├── components/
│   │   ├── Header.astro       # Responsive, keyboard-accessible navigation
│   │   ├── Hero.astro         # Content-driven hero header
│   │   ├── ProjectGrid.astro  # Responsive project cards grid
│   │   ├── Timeline.astro     # Semantic experience and education list
│   │   ├── ContactForm.astro  # Accessible form with 3 submission modes
│   │   └── Footer.astro       # Accessible footer and social links
│   └── styles/
│       └── tokens.css         # Centralized CSS variables and variants
└── tests/
    ├── content.test.ts        # Zod schema validation & duplicate slug tests
    ├── navigation.test.ts     # Internal route mapping and link integrity
    ├── build.test.ts          # Built HTML artifact and landmark verification
    └── tokens.test.ts         # Token definitions and constraint tests
```

---

## 5. Design Token Architecture (`tokens.css`)

All colors, typography, spacing, and geometric rules derive strictly from CSS custom properties defined in `src/styles/tokens.css`. Components **never** hardcode hex colors or ad-hoc spacing values.

### Available Tokens

| Category | Token Name | Meaning |
| :--- | :--- | :--- |
| **Brand Colors** | `--color-brand-primary` | Main interactive brand accent |
| | `--color-brand-hover` | Darker contrast hover state |
| | `--color-brand-muted` | Soft background badge tint |
| **Surfaces** | `--color-bg-base` | Primary canvas background |
| | `--color-bg-surface` | Card and component surface |
| | `--color-bg-elevated` | Secondary nested surface / badges |
| **Typography** | `--color-text-primary` | High-contrast body and heading text |
| | `--color-text-secondary` | Subtitles, descriptions, secondary copy |
| | `--color-text-muted` | Metadata, timestamps, footer copy |
| | `--font-family-base` | Pinned to `Poppins, system-ui, sans-serif` |
| | `--font-size-xs` to `5xl` | Fluid type scale (12px to 48px) |
| **Borders & Focus** | `--color-border-subtle` | Card borders and divider rules |
| | `--color-border-strong` | Input outlines and strong dividers |
| | `--color-focus-ring` | High-visibility keyboard focus indicator |
| **Geometry** | `--radius-sm`, `md`, `lg` | Component corner rounding |
| **Layout** | `--content-max-width` | Max width container (`72rem` / `1152px`) |
| | `--space-section` | Standard vertical section rhythm |

### Aesthetic Constraints

Per project guidelines:
- **Font**: Poppins font only.
- **Forbidden**: Gradients, neon colors, glassmorphism (`backdrop-filter`), and emoji icons.
- **Contrast**: All text meets WCAG 2.2 AA requirements (minimum 4.5:1 for body text; minimum 3:1 for large headings and UI controls).

---

## 6. Visual Variants & How to Switch Them

The template provides two distinct visual variants using design tokens alone:

1. **`editorial` (Default)**:
   - Warm alabaster canvas (`#F9F8F6`).
   - Deep charcoal text (`#1C1B19`).
   - Terracotta/rust brand accent (`#9C4126`).
   - Crisp classic radii (`2px`, `4px`, `8px`).
2. **`studio`**:
   - Pure white canvas (`#FFFFFF`).
   - Deep obsidian text (`#0C1017`).
   - Vibrant cobalt blue brand accent (`#0952C6`).
   - Modern soft radii (`6px`, `10px`, `16px`).

### How to Select a Variant

Switching variants is completely deterministic and **requires zero component modifications**:

#### Option A: Build-time environment variable

```bash
# Build with editorial variant
pnpm run build:editorial

# Build with studio variant
pnpm run build:studio

# Or via THEME variable directly
THEME=studio pnpm build
```

#### Option B: Configure in `src/content/site.json`

Set the `"theme"` field in `src/content/site.json`:

```json
{
  "theme": "studio"
}
```

The `BaseLayout.astro` reads `process.env.THEME || site.theme || 'editorial'` and injects `<html data-theme="...">`.

---

## 7. Structured Content System

Every page is driven by JSON content validated via Zod schemas in `src/content/config.ts`:

### 1. `site.json`
- `clientName`: Display name for the person or company.
- `siteTitle`: Default browser `<title>`.
- `description`: Default meta description.
- `theme`: `"editorial"` or `"studio"`.
- `nav`: Array of `{ label, href }` items.
- `footerText`: Copyright statement.
- `socialLinks`: Array of `{ platform, url, label }`.
- `seo`: Optional OpenGraph and Twitter handle metadata.

### 2. `home.json`
- `heroEyebrow`: Small uppercase subtitle.
- `headline`: Main `<h1>` proposition.
- `supportingCopy`: Intro paragraph.
- `ctaPrimary` & `ctaSecondary`: Buttons `{ label, href }`.
- `highlights`: Metrics array `{ metric, label }`.
- `featuredSectionTitle` & `featuredSectionSubtitle`: Headings for featured projects.

### 3. `about.json`
- `title` & `intro`: Bio overview.
- `bioParagraphs`: Array of narrative strings.
- `skills`: Categorized competencies `{ category, items }`.
- `timeline`: Chronological list `{ period, role, organization, description }`.
- `cta`: Call to action `{ headline, linkText, href }`.

### 4. `projects.json`
- `title` & `subtitle`: Listing header.
- `projects`: Array of case studies:
  - `title`: Project title.
  - `slug`: Unique lowercase slug (e.g. `sentinel-core`).
  - `shortDescription`: Summary for cards.
  - `detailedDescription`: Full context.
  - `techTags`: Technology badges array.
  - `image` & `imageAlt`: Project preview graphic and descriptive alt text.
  - `liveDemoUrl`: Optional live URL.
  - `sourceCodeUrl`: Optional repository URL.
  - `featured`: Boolean indicating if displayed on Home page.

### 5. `contact.json`
- `title` & `description`: Page header.
- `email`: Direct email address.
- `mode`: `"static"`, `"mailto"`, or `"endpoint"`.
- `endpointUrl`: Optional HTTP target when mode is `"endpoint"`.
- `form`: Labels and messaging strings.

---

## 8. Customizing Content Safely

### Adding a Project

1. Open `src/content/projects.json`.
2. Add a new object to the `projects` array:
   ```json
   {
     "title": "New Platform",
     "slug": "new-platform",
     "shortDescription": "High-throughput data platform.",
     "detailedDescription": "Engineered with Clean Architecture...",
     "techTags": ["TypeScript", "PostgreSQL"],
     "image": "/images/project-new.svg",
     "imageAlt": "Architecture diagram for New Platform",
     "liveDemoUrl": "https://example.com/demo",
     "sourceCodeUrl": "https://github.com/example/new",
     "featured": true
   }
   ```
3. Run `pnpm test` to verify that the slug is unique and schema validation passes.

### Removing a Project

Delete the project object from `src/content/projects.json`.

### Adding a Page or Section

1. Create `src/pages/<new-page>.astro`.
2. Wrap content inside `<BaseLayout title="New Page">`.
3. Add the navigation item to `src/content/site.json` in `nav`.
4. Run `pnpm test` to ensure link integrity passes.

---

## 9. Contact Form Modes & Behavior

The contact form supports three distinct, honest modes:

| Mode | Behavior | Safe Default |
| :--- | :--- | :--- |
| **`static`** *(Default)* | Displays a visible disclaimer: *"Notice: This template is in demonstration mode. Submissions are not transmitted over the network."* Form validation runs natively; on submit, an accessible status container informs the user without claiming network delivery. | Yes |
| **`mailto`** | Standard HTML `<form action="mailto:..." method="post">` opening the user's default email client. | Yes |
| **`endpoint`** | Submits a `POST` request to an explicitly configured `endpointUrl` (e.g., Formspree, Formkeep, or custom API). | Requires valid URL |

> [!IMPORTANT]
> The template **never** falsely claims that a message was sent when running in static or unconfigured mode.

---

## 10. Accessibility Practices (WCAG 2.2 AA)

- **Semantic Landmarks**: `<header>`, `<nav aria-label="...">`, `<main id="main-content">`, `<section aria-labelledby="...">`, `<article>`, and `<footer>`.
- **Keyboard Navigation & Skip Link**: Includes `.skip-link` allowing screen-reader and keyboard users to bypass header navigation.
- **Visible Focus States**: Explicit `:focus-visible` with `--color-focus-ring` (2px outline with 3px offset) across all interactive elements.
- **Reduced Motion**: `@media (prefers-reduced-motion: reduce)` resets all transitions and animations to 0ms.
- **Color Independence**: Active navigation states combine bold font weights, color, and a bottom border indicator.
- **Form Accessibility**: All `<input>` and `<textarea>` elements are paired with `<label for="...">`, marked with `aria-required="true"`, and status messages use `role="status"` and `aria-live="polite"`.

---

## 11. Automated Testing & Verification

Run the full automated test suite:

```bash
pnpm test
```

Run TypeScript and Astro template checks:

```bash
pnpm check
```

### What Tests Verify

- **Content Schema**: All 5 content files conform to strict Zod schemas.
- **Duplicate Slugs**: Verifies that duplicate project slugs fail validation.
- **Link Integrity**: All internal navigation links point to existing page routes.
- **Build Output**: Verifies that `index.html`, `about/index.html`, `projects/index.html`, and `contact/index.html` contain semantic landmarks, `<title>`, meta descriptions, `<h1>`, and accessible image `alt` attributes.
- **Design Token Integrity**: Verifies custom properties, lack of gradients/neon, and Poppins font usage.

---

## 12. Lighthouse Test Procedure & Limitations

To run a full Lighthouse audit locally:

1. Build the production site:
   ```bash
   pnpm build
   ```
2. Serve the static build with the preview server:
   ```bash
   pnpm preview
   ```
3. Run Lighthouse CLI against `http://localhost:4321`:
   ```bash
   npx lighthouse http://localhost:4321 --view --preset=desktop
   ```

*Note on Local Environment Limitation:* The Lighthouse CLI requires an active Chromium instance and global or downloadable npm tooling. In sandboxed environments with network isolation, run Lighthouse in the host browser DevTools (Audit / Lighthouse panel) against `pnpm preview`. Because the template emits static HTML with zero framework JavaScript bundles, responsive images, semantic landmarks, and preconnect font headers, it is architected to achieve scores of 95–100 across Performance, Accessibility, Best Practices, and SEO.

---

## 13. How AI Agents Customize This Template

In the Agency automated workflow:
1. The agent copies `templates/site-astro/` into an isolated workspace sandbox (`/workspace`).
2. The agent reads the client brief and modifies only `src/content/*.json` files.
3. The agent chooses `"editorial"` or `"studio"` in `site.json` based on the requested tone.
4. The agent runs `pnpm build && pnpm test` to verify content validity.
5. Zero modifications to `.astro` layout or component logic are required.
