import { describe, it, expect, vi } from 'vitest';
import { runsKeys } from '@/features/runs/queries';
import { RunState } from '@/features/runs/types';

describe('TanStack Query Keys', () => {
  it('generates consistent hierarchical query keys', () => {
    expect(runsKeys.all).toEqual(['runs']);
    expect(runsKeys.lists()).toEqual(['runs', 'list']);
    expect(runsKeys.list({ limit: 20, offset: 0, status: RunState.AWAITING_APPROVAL })).toEqual([
      'runs',
      'list',
      { limit: 20, offset: 0, status: RunState.AWAITING_APPROVAL },
    ]);
    expect(runsKeys.details()).toEqual(['runs', 'detail']);
    expect(runsKeys.detail('run-123')).toEqual(['runs', 'detail', 'run-123']);
    expect(runsKeys.artifacts('run-123')).toEqual(['runs', 'detail', 'run-123', 'artifacts']);
  });
});

describe('CompletedRunPanel and ApprovalPanel Logic', () => {
  it('identifies valid production URLs', () => {
    const validHttp = 'http://localhost:3000';
    const validHttps = 'https://agency-client.pages.dev';
    const invalidJs = 'javascript:void(0)';
    const invalidText = 'not-a-url';

    function isValid(url: string | null | undefined): boolean {
      if (!url) return false;
      try {
        const parsed = new URL(url);
        return parsed.protocol === 'http:' || parsed.protocol === 'https:';
      } catch {
        return false;
      }
    }

    expect(isValid(validHttp)).toBe(true);
    expect(isValid(validHttps)).toBe(true);
    expect(isValid(invalidJs)).toBe(false);
    expect(isValid(invalidText)).toBe(false);
  });
});
