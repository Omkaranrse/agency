/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: 'var(--color-brand-primary)',
          hover: 'var(--color-brand-hover)',
          muted: 'var(--color-brand-muted)',
        },
        bg: {
          base: 'var(--color-bg-base)',
          surface: 'var(--color-bg-surface)',
          elevated: 'var(--color-bg-elevated)',
        },
        text: {
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          muted: 'var(--color-text-muted)',
        },
        border: {
          subtle: 'var(--color-border-subtle)',
          strong: 'var(--color-border-strong)',
        },
        focus: 'var(--color-focus-ring)',
      },
      fontFamily: {
        sans: ['Poppins', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        full: '9999px',
      },
      maxWidth: {
        content: 'var(--content-max-width)',
      },
    },
  },
  plugins: [],
};
