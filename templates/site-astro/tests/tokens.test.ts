import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const TOKENS_PATH = path.resolve(__dirname, '../src/styles/tokens.css');

describe('Centralized Design Tokens Integrity', () => {
  const tokensCss = fs.readFileSync(TOKENS_PATH, 'utf-8');

  it('defines both editorial and studio visual variants', () => {
    expect(tokensCss).toContain('[data-theme="editorial"]');
    expect(tokensCss).toContain('[data-theme="studio"]');
  });

  it('defines required brand, background, text, and border custom properties', () => {
    const requiredTokens = [
      '--color-brand-primary',
      '--color-brand-hover',
      '--color-brand-muted',
      '--color-bg-base',
      '--color-bg-surface',
      '--color-bg-elevated',
      '--color-text-primary',
      '--color-text-secondary',
      '--color-text-muted',
      '--color-border-subtle',
      '--color-border-strong',
      '--color-focus-ring',
      '--radius-sm',
      '--radius-md',
      '--radius-lg',
      '--space-section',
      '--content-max-width',
    ];

    for (const token of requiredTokens) {
      expect(tokensCss).toContain(token);
    }
  });

  it('enforces aesthetic constraints: no gradients, neon colors, or glassmorphism', () => {
    // Prohibited styles per project guidelines
    expect(tokensCss.toLowerCase()).not.toContain('linear-gradient');
    expect(tokensCss.toLowerCase()).not.toContain('radial-gradient');
    expect(tokensCss.toLowerCase()).not.toContain('backdrop-filter');
    expect(tokensCss.toLowerCase()).not.toContain('#00ff'); // Typical neon cyan/green
    expect(tokensCss.toLowerCase()).not.toContain('#ff00ff'); // Neon magenta
  });

  it('enforces Poppins as the designated font family', () => {
    expect(tokensCss).toContain("'Poppins'");
  });
});
