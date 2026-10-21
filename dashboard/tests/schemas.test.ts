import { describe, it, expect } from 'vitest';
import {
  createRunBriefSchema,
  reviseRunSchema,
  cancelRunSchema,
} from '@/features/runs/schemas';

describe('Brief and Run Validation Schemas', () => {
  it('validates a complete, valid client brief', () => {
    const valid = {
      client_name: 'Studio Kura',
      site_type: 'business',
      pagesInput: 'home, about, services, contact',
      tone: 'minimalist and clean',
      content_notes: 'Focus on residential architecture portfolio.',
      project_id: 'studio-kura',
      template_variant: 'standard',
    };

    const result = createRunBriefSchema.safeParse(valid);
    expect(result.success).toBe(true);
  });

  it('rejects brief with missing client name', () => {
    const invalid = {
      client_name: '   ',
      site_type: 'business',
      pagesInput: 'home',
      tone: 'clean',
      content_notes: 'Some notes',
    };

    const result = createRunBriefSchema.safeParse(invalid);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('Client name is required');
    }
  });

  it('rejects brief with empty pages', () => {
    const invalid = {
      client_name: 'Acme Corp',
      site_type: 'business',
      pagesInput: '   ',
      tone: 'clean',
      content_notes: 'Some notes',
    };

    const result = createRunBriefSchema.safeParse(invalid);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('At least one page is required');
    }
  });

  it('validates revision feedback requires non-empty comment', () => {
    const empty = { comment: '   ' };
    expect(reviseRunSchema.safeParse(empty).success).toBe(false);

    const valid = { comment: 'Please adjust primary button contrast and increase typography size.' };
    expect(reviseRunSchema.safeParse(valid).success).toBe(true);
  });

  it('validates cancellation schema allows optional reason', () => {
    expect(cancelRunSchema.safeParse({}).success).toBe(true);
    expect(cancelRunSchema.safeParse({ reason: 'Client requested postponement' }).success).toBe(true);
  });
});
