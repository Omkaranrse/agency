import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const DIST_DIR = path.resolve(__dirname, '../dist');

describe('Generated Static Pages and Semantic Output', () => {
  it('verifies all four static pages are generated in dist/', () => {
    const requiredHtmlFiles = [
      path.join(DIST_DIR, 'index.html'),
      path.join(DIST_DIR, 'about/index.html'),
      path.join(DIST_DIR, 'projects/index.html'),
      path.join(DIST_DIR, 'contact/index.html'),
    ];

    for (const filePath of requiredHtmlFiles) {
      expect(fs.existsSync(filePath), `Missing expected build artifact: ${filePath}`).toBe(true);
    }
  });

  it('verifies Home page contains title, description, h1, and skip link', () => {
    const indexHtml = fs.readFileSync(path.join(DIST_DIR, 'index.html'), 'utf-8');

    expect(indexHtml).toContain('<title>');
    expect(indexHtml).toContain('<meta name="description"');
    expect(indexHtml).toContain('class="skip-link"');
    expect(indexHtml).toContain('<h1');
    expect(indexHtml).toContain('<main id="main-content"');
  });

  it('verifies About page contains title, description, and timeline', () => {
    const aboutHtml = fs.readFileSync(path.join(DIST_DIR, 'about/index.html'), 'utf-8');

    expect(aboutHtml).toContain('About Devon Miller');
    expect(aboutHtml).toContain('<h1');
    expect(aboutHtml).toContain('Technical Disciplines & Expertise');
    expect(aboutHtml).toContain('Experience & Education');
  });

  it('verifies Projects page contains project cards and alt tags on images', () => {
    const projectsHtml = fs.readFileSync(path.join(DIST_DIR, 'projects/index.html'), 'utf-8');

    expect(projectsHtml).toContain('Projects &amp; Case Studies');
    expect(projectsHtml).toContain('Sentinel Core');
    expect(projectsHtml).toContain('alt="Architectural diagram');
  });

  it('verifies Contact page contains accessible form elements and labels', () => {
    const contactHtml = fs.readFileSync(path.join(DIST_DIR, 'contact/index.html'), 'utf-8');

    expect(contactHtml).toContain('<form id="contact-form"');
    expect(contactHtml).toContain('for="contact-name"');
    expect(contactHtml).toContain('id="contact-name"');
    expect(contactHtml).toContain('for="contact-email"');
    expect(contactHtml).toContain('id="contact-email"');
    expect(contactHtml).toContain('for="contact-message"');
    expect(contactHtml).toContain('id="contact-message"');
    expect(contactHtml).toContain('role="status"');
  });

  it('verifies static assets exist in dist/', () => {
    expect(fs.existsSync(path.join(DIST_DIR, 'favicon.svg'))).toBe(true);
    expect(fs.existsSync(path.join(DIST_DIR, 'images/project-sentinel.svg'))).toBe(true);
    expect(fs.existsSync(path.join(DIST_DIR, 'images/project-prism.svg'))).toBe(true);
  });
});
