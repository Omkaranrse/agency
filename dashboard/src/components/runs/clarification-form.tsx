'use client';

import * as React from 'react';
import { HelpCircle, Send, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

export interface ClarificationFormProps {
  questions: string[];
  onSubmitAnswers: (answers: Record<string, string>) => void;
  isSubmitting?: boolean;
}

export function ClarificationForm({
  questions,
  onSubmitAnswers,
  isSubmitting = false,
}: ClarificationFormProps) {
  const [answers, setAnswers] = React.useState<Record<string, string>>({});

  const handleTextChange = (idx: number, val: string) => {
    setAnswers((prev) => ({ ...prev, [String(idx)]: val }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmitAnswers(answers);
  };

  if (!questions || questions.length === 0) return null;

  return (
    <div className="rounded border border-warning/30 bg-warning-surface/30 p-4 space-y-4">
      <div className="flex items-start gap-2.5">
        <HelpCircle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
        <div>
          <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">
            Clarification Required by Project Manager Agent
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
            The brief contains ambiguities that require clarification before the design and technical specification can be finalized.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 pt-1">
        {questions.map((q, idx) => (
          <div key={idx} className="space-y-1.5 rounded border border-border bg-surface p-3">
            <label className="block text-xs font-medium text-foreground">
              {idx + 1}. {q}
            </label>
            <Textarea
              rows={2}
              placeholder="Provide clarifying details..."
              value={answers[String(idx)] || ''}
              onChange={(e) => handleTextChange(idx, e.target.value)}
              disabled={isSubmitting}
            />
          </div>
        ))}

        <div className="flex items-center justify-end">
          <Button type="submit" size="sm" isLoading={isSubmitting}>
            <Send className="h-3 w-3 mr-1" />
            <span>Submit Clarification Answers</span>
          </Button>
        </div>
      </form>
    </div>
  );
}
