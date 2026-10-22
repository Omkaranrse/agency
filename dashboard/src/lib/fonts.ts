// Safe offline-compatible font contract for Poppins
// Provides CSS variable and font-family without blocking on external Google Fonts CDN fetches
export const poppins = {
  variable: 'font-poppins',
  className: 'font-poppins',
  style: {
    fontFamily: "'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
};
