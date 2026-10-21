import Link from 'next/link';
import { ArrowLeft, Compass } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center bg-background text-foreground">
      <div className="flex h-12 w-12 items-center justify-center rounded bg-surface-raised border border-border text-muted-foreground mb-4">
        <Compass className="h-6 w-6" aria-hidden="true" />
      </div>
      <h1 className="text-xl font-semibold tracking-tight text-foreground mb-1">
        Page Not Found
      </h1>
      <p className="text-xs text-muted-foreground max-w-sm mb-6">
        The requested dashboard route does not exist or has been relocated.
      </p>
      <Button asChild variant="outline" size="sm">
        <Link href="/runs" className="inline-flex items-center gap-1.5">
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Return to Runs</span>
        </Link>
      </Button>
    </div>
  );
}
