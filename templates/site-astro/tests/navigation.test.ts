import { describe, it, expect } from 'vitest';
import rawSite from '../src/content/site.json';
import rawHome from '../src/content/home.json';
import rawAbout from '../src/content/about.json';
import fs from 'node:fs';
import path from 'node:path';

const VALID_ROUTES = new Set(['/', '/about', '/projects', '/contact']);

describe('Navigation and Link Integrity', () => {
  it('ensures all site navigation links point to valid routes', () => {
    for (const item of rawSite.nav) {
      expect(VALID_ROUTES.has(item.href)).toBe(true);
    }
  });

  it('ensures Home CTAs link to valid internal routes', () => {
    expect(VALID_ROUTES.has(rawHome.ctaPrimary.href)).toBe(true);
    expect(VALID_ROUTES.has(rawHome.ctaSecondary.href)).toBe(true);
  });

  it('ensures About CTA links to valid internal route', () => {
    expect(VALID_ROUTES.has(rawAbout.cta.href)).toBe(true);
  });

  it('ensures all four required page files exist in src/pages/', () => {
    const pagesDir = path.resolve(__dirname, '../src/pages');
    const requiredPages = ['index.astro', 'about.astro', 'projects.astro', 'contact.astro'];

    for (const page of requiredPages) {
      expect(fs.existsSync(path.join(pagesDir, page))).toBe(true);
    }
  });
});
