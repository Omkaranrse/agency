import { z } from 'zod';

export const createRunBriefSchema = z.object({
  client_name: z
    .string()
    .trim()
    .min(1, 'Client name is required.')
    .max(100, 'Client name must be 100 characters or fewer.'),
  site_type: z
    .string()
    .trim()
    .min(1, 'Site archetype is required.')
    .max(100, 'Site archetype must be 100 characters or fewer.'),
  pagesInput: z
    .string()
    .trim()
    .min(1, 'At least one page is required (e.g. home, about, contact).'),
  tone: z
    .string()
    .trim()
    .min(1, 'Design tone and aesthetic is required.')
    .max(200, 'Tone must be 200 characters or fewer.'),
  content_notes: z
    .string()
    .trim()
    .min(1, 'Content requirements and brand notes are required.')
    .max(5000, 'Content notes must be 5000 characters or fewer.'),
  project_id: z
    .string()
    .trim()
    .max(100, 'Project ID must be 100 characters or fewer.')
    .optional()
    .or(z.literal('')),
  template_variant: z
    .string()
    .trim()
    .max(50, 'Template variant must be 50 characters or fewer.')
    .optional()
    .or(z.literal('')),
});

export type CreateRunBriefFormValues = z.infer<typeof createRunBriefSchema>;

export const reviseRunSchema = z.object({
  comment: z
    .string()
    .trim()
    .min(1, 'Feedback comment cannot be empty.')
    .max(1000, 'Feedback must be 1000 characters or fewer.'),
});

export type ReviseRunFormValues = z.infer<typeof reviseRunSchema>;

export const cancelRunSchema = z.object({
  reason: z
    .string()
    .trim()
    .max(200, 'Reason must be 200 characters or fewer.')
    .optional(),
});

export type CancelRunFormValues = z.infer<typeof cancelRunSchema>;
