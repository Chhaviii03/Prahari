/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        sev: {
          critical: '#FF3B30',
          active: '#FF9F0A',
          watch: '#FFD60A',
          ok: '#30D158',
          stale: '#8E8E93',
        },
        bg: {
          base: '#0B0F14',
          surface: '#151A21',
          elevated: '#1C2229',
        },
        text: {
          primary: '#F2F4F7',
          secondary: '#9CA3AF',
        },
        accent: '#0A84FF',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
