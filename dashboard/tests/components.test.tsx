import React from 'react';
import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { RunStatusBadge } from '@/components/runs/run-status';
import { RunPreview } from '@/components/runs/run-preview';
import { ClarificationForm } from '@/components/runs/clarification-form';

describe('RunStatusBadge Component', () => {
  it('renders status text and revision badge', () => {
    const html = renderToStaticMarkup(
      <RunStatusBadge status="AWAITING_APPROVAL" revision={2} />
    );

    expect(html).toContain('Awaiting Approval');
    expect(html).toContain('r2');
  });

  it('renders terminal statuses without crashing', () => {
    const htmlCompleted = renderToStaticMarkup(<RunStatusBadge status="COMPLETED" />);
    expect(htmlCompleted).toContain('Completed');

    const htmlFailed = renderToStaticMarkup(<RunStatusBadge status="FAILED" />);
    expect(htmlFailed).toContain('Failed');

    const htmlCancelled = renderToStaticMarkup(<RunStatusBadge status="CANCELLED" />);
    expect(htmlCancelled).toContain('Cancelled');
  });
});

describe('RunPreview Component', () => {
  it('renders unavailable placeholder when previewUrl is missing', () => {
    const html = renderToStaticMarkup(
      <RunPreview previewUrl={null} status="PLANNING" currentStage="planning" />
    );

    expect(html).toContain('Preview Not Available Yet');
    expect(html).toContain('Current stage:');
  });

  it('renders iframe and toolbar when valid previewUrl is provided', () => {
    const html = renderToStaticMarkup(
      <RunPreview
        previewUrl="https://agency-preview.pages.dev"
        status="AWAITING_APPROVAL"
        currentStage="awaiting_approval"
      />
    );

    expect(html).toContain('Website prototype preview');
    expect(html).toContain('src="https://agency-preview.pages.dev"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
  });

  it('rejects unsafe protocol URLs from rendering in iframe', () => {
    const html = renderToStaticMarkup(
      <RunPreview
        previewUrl="javascript:alert(1)"
        status="BUILDING"
        currentStage="building"
      />
    );

    expect(html).toContain('Preview Not Available Yet');
    expect(html).not.toContain('<iframe');
  });
});

describe('ClarificationForm Component', () => {
  it('renders PM agent questions and submit button', () => {
    const questions = [
      'What primary call to action should be featured on the homepage?',
      'Do you require an integrated scheduling calendar?',
    ];

    const html = renderToStaticMarkup(
      <ClarificationForm
        questions={questions}
        onSubmitAnswers={() => {}}
      />
    );

    expect(html).toContain('What primary call to action');
    expect(html).toContain('Do you require an integrated scheduling calendar');
    expect(html).toContain('Submit Clarification Answers');
  });
});
