/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        sev: {
          critical: '#DC2626',
          active: '#D97706',
          watch: '#CA8A04',
          ok: '#15803D',
          stale: '#6B7280',
        },
        bg: {
          base: '#FAF8F8',
          surface: '#FFFFFF',
          elevated: '#FFF1EC',
        },
        ink: {
          primary: '#0F172A',
          secondary: '#475569',
        },
        accent: {
          DEFAULT: '#B4533A',
          strong: '#9A3F2A',
          soft: '#FFF1EC',
          muted: '#FFC2B1',
          peach: '#F5A892',
        },
        line: {
          DEFAULT: '#E5E7EB',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(17, 24, 39, 0.04), 0 4px 16px rgba(17, 24, 39, 0.04)',
        soft: '0 8px 30px rgba(253, 186, 116, 0.12)',
      },
    },
  },
  plugins: [],
}
