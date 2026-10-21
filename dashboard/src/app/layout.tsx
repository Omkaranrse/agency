import type { Metadata } from 'next';
import { poppins } from '@/lib/fonts';
import { ThemeProvider } from '@/components/theme/theme-provider';
import { QueryProvider } from '@/components/providers/query-provider';
import './globals.css';

export const metadata: Metadata = {
  title: 'Agency — Internal Ops Dashboard',
  description: 'AI software agency operator dashboard for website runs, previews, and QA.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={poppins.variable} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var stored = localStorage.getItem('agency-theme');
                  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  if (stored === 'dark' || (!stored && prefersDark) || (stored === 'system' && prefersDark)) {
                    document.documentElement.classList.add('dark');
                  } else {
                    document.documentElement.classList.remove('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="antialiased min-h-screen">
        <QueryProvider>
          <ThemeProvider defaultTheme="system">
            {children}
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
