import { z } from 'zod';

// ==============================================================================
// Site Content Schema
// ==============================================================================
export const NavItemSchema = z.object({
  label: z.string().min(1, 'Navigation label is required'),
  href: z.string().min(1, 'Navigation href is required'),
});

export const SocialLinkSchema = z.object({
  platform: z.string().min(1, 'Social platform name is required'),
  url: z.string().url('Social link must be a valid URL'),
  label: z.string().min(1, 'Accessible label is required'),
});

export const SiteContentSchema = z.object({
  clientName: z.string().min(1, 'Client name is required'),
  siteTitle: z.string().min(1, 'Site title is required'),
  description: z.string().min(1, 'Description is required'),
  theme: z.enum(['editorial', 'studio']).default('editorial'),
  nav: z.array(NavItemSchema).min(1, 'At least one navigation item required'),
  footerText: z.string().min(1, 'Footer text is required'),
  socialLinks: z.array(SocialLinkSchema),
  seo: z.object({
    ogImage: z.string().optional(),
    twitterHandle: z.string().optional(),
  }).default({}),
});

export type SiteContent = z.infer<typeof SiteContentSchema>;

// ==============================================================================
// Home Content Schema
// ==============================================================================
export const HighlightMetricSchema = z.object({
  metric: z.string().min(1, 'Metric value is required'),
  label: z.string().min(1, 'Metric label is required'),
});

export const HomeContentSchema = z.object({
  heroEyebrow: z.string().min(1, 'Hero eyebrow is required'),
  headline: z.string().min(1, 'Headline is required'),
  supportingCopy: z.string().min(1, 'Supporting copy is required'),
  ctaPrimary: z.object({
    label: z.string().min(1, 'Primary CTA label required'),
    href: z.string().min(1, 'Primary CTA href required'),
  }),
  ctaSecondary: z.object({
    label: z.string().min(1, 'Secondary CTA label required'),
    href: z.string().min(1, 'Secondary CTA href required'),
  }),
  highlights: z.array(HighlightMetricSchema).default([]),
  featuredSectionTitle: z.string().min(1, 'Featured section title required'),
  featuredSectionSubtitle: z.string().min(1, 'Featured section subtitle required'),
});

export type HomeContent = z.infer<typeof HomeContentSchema>;

// ==============================================================================
// About Content Schema
// ==============================================================================
export const SkillCategorySchema = z.object({
  category: z.string().min(1, 'Skill category is required'),
  items: z.array(z.string().min(1)).min(1, 'At least one skill item required'),
});

export const TimelineItemSchema = z.object({
  period: z.string().min(1, 'Period is required'),
  role: z.string().min(1, 'Role or degree is required'),
  organization: z.string().min(1, 'Organization or institution is required'),
  description: z.string().min(1, 'Description is required'),
});

export const AboutContentSchema = z.object({
  title: z.string().min(1, 'Page title is required'),
  intro: z.string().min(1, 'Introductory summary is required'),
  bioParagraphs: z.array(z.string().min(1)).min(1, 'At least one bio paragraph required'),
  skills: z.array(SkillCategorySchema).min(1, 'At least one skill category required'),
  timeline: z.array(TimelineItemSchema).min(1, 'At least one timeline entry required'),
  cta: z.object({
    headline: z.string().min(1, 'CTA headline required'),
    linkText: z.string().min(1, 'CTA link text required'),
    href: z.string().min(1, 'CTA href required'),
  }),
});

export type AboutContent = z.infer<typeof AboutContentSchema>;

// ==============================================================================
// Projects Content Schema
// ==============================================================================
export const ProjectItemSchema = z.object({
  title: z.string().min(1, 'Project title is required'),
  slug: z.string().regex(/^[a-z0-9-]+$/, 'Slug must be lowercase alphanumeric with hyphens'),
  shortDescription: z.string().min(1, 'Short description is required'),
  detailedDescription: z.string().min(1, 'Detailed description is required'),
  techTags: z.array(z.string().min(1)).min(1, 'At least one technology tag required'),
  image: z.string().optional(),
  imageAlt: z.string().min(1, 'Meaningful alt text is required when image is provided'),
  liveDemoUrl: z.string().url('Live demo must be a valid URL').optional().or(z.literal('')),
  sourceCodeUrl: z.string().url('Source code must be a valid URL').optional().or(z.literal('')),
  featured: z.boolean().default(false),
});

export const ProjectsContentSchema = z.object({
  title: z.string().min(1, 'Projects title is required'),
  subtitle: z.string().min(1, 'Projects subtitle is required'),
  projects: z.array(ProjectItemSchema).min(1, 'At least one project is required'),
}).refine(
  (data) => {
    const slugs = data.projects.map((p) => p.slug);
    return new Set(slugs).size === slugs.length;
  },
  {
    message: 'Duplicate project slugs detected. Every project slug must be unique.',
    path: ['projects'],
  }
);

export type ProjectItem = z.infer<typeof ProjectItemSchema>;
export type ProjectsContent = z.infer<typeof ProjectsContentSchema>;

// ==============================================================================
// Contact Content Schema
// ==============================================================================
export const ContactContentSchema = z.object({
  title: z.string().min(1, 'Contact title is required'),
  description: z.string().min(1, 'Contact description is required'),
  email: z.string().email('Contact email must be a valid email address'),
  mode: z.enum(['mailto', 'static', 'endpoint']).default('static'),
  endpointUrl: z.string().url().optional(),
  form: z.object({
    nameLabel: z.string().min(1, 'Name label is required'),
    emailLabel: z.string().min(1, 'Email label is required'),
    messageLabel: z.string().min(1, 'Message label is required'),
    submitLabel: z.string().min(1, 'Submit button label is required'),
    privacyNote: z.string().min(1, 'Privacy note is required'),
    staticModeNotice: z.string().min(1, 'Static mode notice is required'),
    successMessage: z.string().min(1, 'Success message is required'),
  }),
});

export type ContactContent = z.infer<typeof ContactContentSchema>;

export const collections = {};
