'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  AlertCircle,
  Sparkles,
  Send,
  Building2,
  FileCode,
  Layers,
  Compass,
  CheckCircle2,
  Cpu,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { GlowCard } from '@/components/framer/glow-card';
import { ShimmerButton } from '@/components/framer/shimmer-button';
import {
  createRunBriefSchema,
  type CreateRunBriefFormValues,
} from '@/features/runs/schemas';
import { useCreateRun } from '@/features/runs/mutations';
import { parseApiError } from '@/lib/api/config';
import { containerStaggerVariants, itemFadeUpVariants } from '@/lib/motion';

export default function NewRunPage() {
  const router = useRouter();
  const createMutation = useCreateRun();
  const [submissionError, setSubmissionError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<CreateRunBriefFormValues>({
    resolver: zodResolver(createRunBriefSchema),
    mode: 'onBlur',
    defaultValues: {
      client_name: '',
      site_type: 'business',
      pagesInput: 'home, about, services, contact',
      tone: 'Nordic minimalism, restrained typography, high contrast',
      content_notes: '',
      project_id: '',
      template_variant: 'standard',
    },
  });

  const formValues = watch();

  const parsedPages = React.useMemo(() => {
    return (formValues.pagesInput || '')
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean);
  }, [formValues.pagesInput]);

  const onSubmit = async (values: CreateRunBriefFormValues) => {
    setSubmissionError(null);

    const rawPages = values.pagesInput
      .split(',')
      .map((p) => p.trim().toLowerCase())
      .filter(Boolean);

    const pages = rawPages.length > 0 ? rawPages : ['home'];

    const idempotencyKey =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `idem-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    try {
      const response = await createMutation.mutateAsync({
        brief: {
          client_name: values.client_name.trim(),
          site_type: values.site_type.trim(),
          pages,
          tone: values.tone.trim(),
          content_notes: values.content_notes.trim(),
        },
        project_id: values.project_id?.trim() || undefined,
        template_variant: values.template_variant?.trim() || undefined,
        idempotency_key: idempotencyKey,
      });

      router.push(`/runs/${response.run_id}`);
    } catch (err) {
      const parsed = parseApiError(err);
      setSubmissionError(parsed.message);
    }
  };

  const isPending = isSubmitting || createMutation.isPending;

  return (
    <div className="space-y-6 max-w-5xl pb-12">
      <PageHeader
        title="Project Brief Intake — Mission Setup"
        description="Configure client requirements to trigger autonomous PM specification, UI design tokens, sandbox assembly, and automated QA verification."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link href="/runs" className="inline-flex items-center gap-1.5">
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Back to runs</span>
            </Link>
          </Button>
        }
      />

      {submissionError && (
        <div
          role="alert"
          className="rounded border border-danger/40 bg-danger-surface p-3.5 text-xs text-danger flex items-start gap-2.5 shadow-xs"
        >
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold block">Failed to initialize run</span>
            <span className="text-[11px] leading-relaxed block mt-0.5 font-mono">
              {submissionError}
            </span>
          </div>
        </div>
      )}

      {/* Quick Template Presets */}
      <div className="p-3 rounded-lg border border-border bg-surface-raised/40 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
          <Sparkles className="h-3.5 w-3.5 text-accent" />
          <span>Quick Project Archetypes:</span>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {[
            {
              label: 'SaaS Platform',
              client: 'VoxelFlow AI',
              type: 'saas',
              pages: 'home, features, pricing, docs, contact',
              tone: 'Deep indigo, high precision telemetry, futuristic monospace accents',
              notes: 'Focus on developer productivity, real-time collaboration, and SOC2 compliance.',
            },
            {
              label: 'Design Agency',
              client: 'Koto Studio NYC',
              type: 'portfolio',
              pages: 'home, work, philosophy, team, inquiry',
              tone: 'Editorial Swiss typography, generous whitespace, warm terracotta tones',
              notes: 'Highlight global brand identity case studies, awards, and design philosophy.',
            },
            {
              label: 'Architecture',
              client: 'Apex Mass Timber',
              type: 'business',
              pages: 'home, about, projects, sustainability, contact',
              tone: 'Nordic minimalism, restrained typography, mass timber accents',
              notes: 'Specialize in sustainable commercial buildings, carbon-negative CLT engineering.',
            },
            {
              label: 'Commerce',
              client: 'Lumina Ceramics',
              type: 'ecommerce',
              pages: 'home, shop, collections, artisans, checkout',
              tone: 'Handcrafted earthy warmth, organic earth tones, serene photography',
              notes: 'Small-batch artisanal ceramics crafted in Kyoto and shipped worldwide.',
            },
          ].map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => {
                setValue('client_name', preset.client, { shouldValidate: true });
                setValue('site_type', preset.type as any, { shouldValidate: true });
                setValue('pagesInput', preset.pages, { shouldValidate: true });
                setValue('tone', preset.tone, { shouldValidate: true });
                setValue('content_notes', preset.notes, { shouldValidate: true });
              }}
              className="px-2.5 py-1 rounded text-xs font-medium bg-surface border border-border hover:border-accent/40 hover:text-accent transition-colors"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Two Column Grid: Form & Blueprint Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Form Column (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="space-y-5 rounded-lg border border-border bg-surface p-5 shadow-xs"
            noValidate
          >
            {/* Step 1: Identity */}
            <div className="space-y-3.5">
              <div className="flex items-center gap-2 pb-2 border-b border-border">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/15 text-accent text-[11px] font-mono font-semibold">
                  1
                </span>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Client Identity & Archetype
                </h3>
              </div>

              {/* Client Name */}
              <div className="space-y-1.5">
                <label htmlFor="client_name" className="block text-xs font-medium text-foreground">
                  Client or Brand Name <span className="text-danger">*</span>
                </label>
                <Input
                  id="client_name"
                  placeholder="e.g. Apex Mass Timber Architecture"
                  disabled={isPending}
                  error={Boolean(errors.client_name)}
                  {...register('client_name')}
                />
                {errors.client_name && (
                  <p className="text-[11px] text-danger">{errors.client_name.message}</p>
                )}
              </div>

              {/* Site Archetype */}
              <div className="space-y-1.5">
                <label htmlFor="site_type" className="block text-xs font-medium text-foreground">
                  Site Archetype <span className="text-danger">*</span>
                </label>
                <Select id="site_type" disabled={isPending} {...register('site_type')}>
                  <option value="business">Business & Professional Services</option>
                  <option value="portfolio">Portfolio & Creative Agency</option>
                  <option value="saas">SaaS & Technology Product</option>
                  <option value="ecommerce">E-Commerce & Retail Catalog</option>
                  <option value="restaurant">Hospitality & Dining</option>
                </Select>
                {errors.site_type && (
                  <p className="text-[11px] text-danger">{errors.site_type.message}</p>
                )}
              </div>
            </div>

            {/* Step 2: Architecture & Content */}
            <div className="space-y-3.5 pt-2">
              <div className="flex items-center gap-2 pb-2 border-b border-border">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/15 text-accent text-[11px] font-mono font-semibold">
                  2
                </span>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Pages & Design Directives
                </h3>
              </div>

              {/* Requested Pages */}
              <div className="space-y-1.5">
                <label htmlFor="pagesInput" className="block text-xs font-medium text-foreground">
                  Requested Site Pages (comma-separated) <span className="text-danger">*</span>
                </label>
                <Input
                  id="pagesInput"
                  placeholder="e.g. home, about, projects, team, contact"
                  disabled={isPending}
                  error={Boolean(errors.pagesInput)}
                  {...register('pagesInput')}
                />
                <p className="text-[10px] text-muted-foreground">
                  Each page will be compiled with authentic section content, typography, and Astro components.
                </p>
                {errors.pagesInput && (
                  <p className="text-[11px] text-danger">{errors.pagesInput.message}</p>
                )}
              </div>

              {/* Tone and Aesthetic */}
              <div className="space-y-1.5">
                <label htmlFor="tone" className="block text-xs font-medium text-foreground">
                  Design Tone & Aesthetic <span className="text-danger">*</span>
                </label>
                <Input
                  id="tone"
                  placeholder="e.g. Nordic minimalism, restrained typography, mass timber accents"
                  disabled={isPending}
                  error={Boolean(errors.tone)}
                  {...register('tone')}
                />
                {errors.tone && (
                  <p className="text-[11px] text-danger">{errors.tone.message}</p>
                )}
              </div>

              {/* Content Notes */}
              <div className="space-y-1.5">
                <label htmlFor="content_notes" className="block text-xs font-medium text-foreground">
                  Content Directives & Value Propositions <span className="text-danger">*</span>
                </label>
                <Textarea
                  id="content_notes"
                  rows={4}
                  placeholder="Specify key client copy guidelines, target audience demographics, value propositions, and calls to action..."
                  disabled={isPending}
                  error={Boolean(errors.content_notes)}
                  {...register('content_notes')}
                />
                {errors.content_notes && (
                  <p className="text-[11px] text-danger">{errors.content_notes.message}</p>
                )}
              </div>
            </div>

            {/* Step 3: Technical Routing Override */}
            <div className="space-y-3.5 pt-2">
              <div className="flex items-center gap-2 pb-2 border-b border-border">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-surface-raised text-muted-foreground text-[11px] font-mono font-semibold">
                  3
                </span>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Routing Parameters (Optional)
                </h3>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="project_id" className="block text-xs font-medium text-muted-foreground">
                  Custom Project ID Slug
                </label>
                <Input
                  id="project_id"
                  placeholder="e.g. apex-architecture"
                  disabled={isPending}
                  error={Boolean(errors.project_id)}
                  {...register('project_id')}
                />
                <p className="text-[10px] text-muted-foreground">
                  Optional URL slug. If left blank, it is automatically derived from the brand name.
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
              <Button asChild variant="outline" size="sm" disabled={isPending}>
                <Link href="/runs">Cancel</Link>
              </Button>

              <ShimmerButton
                type="submit"
                size="default"
                isLoading={isPending}
                disabled={isPending}
              >
                <Send className="h-3.5 w-3.5 mr-1" />
                <span>Initialize Pipeline & Launch</span>
              </ShimmerButton>
            </div>
          </form>
        </div>

        {/* Live Project Blueprint Column (5 cols) */}
        <div className="lg:col-span-5 sticky top-20 space-y-4">
          <GlowCard className="p-4" glowColor="rgba(84, 225, 193, 0.15)">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <FileCode className="h-4 w-4 text-accent" />
                <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Live Brief Blueprint
                </h4>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-raised border border-border text-muted-foreground">
                Preview
              </span>
            </div>

            <div className="mt-3.5 space-y-3 text-xs">
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block">
                  Target Client
                </span>
                <span className="font-semibold text-foreground text-sm">
                  {formValues.client_name?.trim() || 'Untitled Project'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block">
                    Archetype
                  </span>
                  <span className="font-mono text-accent capitalize text-xs">
                    {formValues.site_type || 'business'}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block">
                    Target Pages
                  </span>
                  <span className="font-mono text-foreground text-xs">
                    {parsedPages.length} pages
                  </span>
                </div>
              </div>

              {/* Pages Pill Tags */}
              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block mb-1.5">
                  Page Structure
                </span>
                <div className="flex flex-wrap gap-1">
                  {parsedPages.map((page, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded text-[10px] font-mono bg-surface-raised border border-border text-foreground"
                    >
                      /{page}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block">
                  Aesthetic Directive
                </span>
                <span className="text-xs text-muted-foreground block line-clamp-2">
                  {formValues.tone || 'Default agency style'}
                </span>
              </div>

              {/* Agent Orchestration Readiness */}
              <div className="pt-3 border-t border-border space-y-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground block">
                  Agent Pipeline Routing
                </span>
                <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <CheckCircle2 className="h-3 w-3 text-success" />
                    <span>PMAgent: Spec</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <CheckCircle2 className="h-3 w-3 text-success" />
                    <span>Designer: Tokens</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <CheckCircle2 className="h-3 w-3 text-success" />
                    <span>Builder: Astro AST</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <CheckCircle2 className="h-3 w-3 text-success" />
                    <span>QAService: Checks</span>
                  </div>
                </div>
              </div>
            </div>
          </GlowCard>
        </div>
      </div>
    </div>
  );
}
