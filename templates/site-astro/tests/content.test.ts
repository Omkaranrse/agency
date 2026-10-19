import { describe, it, expect } from 'vitest';
import rawSite from '../src/content/site.json';
import rawHome from '../src/content/home.json';
import rawAbout from '../src/content/about.json';
import rawProjects from '../src/content/projects.json';
import rawContact from '../src/content/contact.json';
import {
  SiteContentSchema,
  HomeContentSchema,
  AboutContentSchema,
  ProjectsContentSchema,
  ContactContentSchema,
  ProjectItemSchema,
} from '../src/content/config';

describe('Structured Content Schema Validation', () => {
  it('validates site.json conforms to SiteContentSchema', () => {
    const parsed = SiteContentSchema.safeParse(rawSite);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.clientName).toBeTruthy();
      expect(parsed.data.nav.length).toBeGreaterThan(0);
    }
  });

  it('validates home.json conforms to HomeContentSchema', () => {
    const parsed = HomeContentSchema.safeParse(rawHome);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.headline).toBeTruthy();
      expect(parsed.data.ctaPrimary.href).toBeTruthy();
    }
  });

  it('validates about.json conforms to AboutContentSchema', () => {
    const parsed = AboutContentSchema.safeParse(rawAbout);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.skills.length).toBeGreaterThan(0);
      expect(parsed.data.timeline.length).toBeGreaterThan(0);
    }
  });

  it('validates projects.json conforms to ProjectsContentSchema', () => {
    const parsed = ProjectsContentSchema.safeParse(rawProjects);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.projects.length).toBeGreaterThan(0);
    }
  });

  it('validates contact.json conforms to ContactContentSchema', () => {
    const parsed = ContactContentSchema.safeParse(rawContact);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.email).toContain('@');
      expect(['mailto', 'static', 'endpoint']).toContain(parsed.data.mode);
    }
  });

  it('rejects duplicate project slugs', () => {
    const duplicateProjects = {
      title: 'Projects',
      subtitle: 'Subtitle',
      projects: [
        {
          title: 'Project 1',
          slug: 'duplicate-slug',
          shortDescription: 'Desc 1',
          detailedDescription: 'Detailed 1',
          techTags: ['TypeScript'],
          imageAlt: 'Alt text',
        },
        {
          title: 'Project 2',
          slug: 'duplicate-slug',
          shortDescription: 'Desc 2',
          detailedDescription: 'Detailed 2',
          techTags: ['Node.js'],
          imageAlt: 'Alt text',
        },
      ],
    };

    const parsed = ProjectsContentSchema.safeParse(duplicateProjects);
    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      const messages = parsed.error.issues.map((i) => i.message);
      expect(messages).toContain(
        'Duplicate project slugs detected. Every project slug must be unique.'
      );
    }
  });

  it('rejects project without imageAlt when image is specified', () => {
    const invalidProject = {
      title: 'Test',
      slug: 'test-slug',
      shortDescription: 'Desc',
      detailedDescription: 'Detailed',
      techTags: ['TypeScript'],
      image: '/images/test.svg',
      imageAlt: '', // Missing alt
    };

    const parsed = ProjectItemSchema.safeParse(invalidProject);
    expect(parsed.success).toBe(false);
  });

  it('rejects invalid email address in contact content', () => {
    const invalidContact = {
      ...rawContact,
      email: 'not-an-email',
    };

    const parsed = ContactContentSchema.safeParse(invalidContact);
    expect(parsed.success).toBe(false);
  });
});
