/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./templates/**/*.html",
    "./frontend/**/*.py",
    "./static/js/src/**/*.js",
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#FBEBED', 100: '#F5D0D5', 200: '#EBA1AA', 300: '#E07280',
          400: '#C14A57', 500: '#A8323F', 600: '#7A1F2B', 700: '#5E161F',
          800: '#450F16', 900: '#2C090E',
          DEFAULT: 'var(--color-primary)',
          strong: 'var(--color-primary-strong)',
        },
        secondary: {
          50: '#E6F4EE', 100: '#C2E5D5', 200: '#85CBAB', 300: '#4DB185',
          400: '#2FA37A', 500: '#1F7A5A', 600: '#186045', 700: '#114730',
          800: '#0A2F20', 900: '#051710',
          DEFAULT: 'var(--color-secondary)',
        },
        accent: {
          50: '#FDF4E3', 100: '#FAE6BF', 200: '#F5CE7F', 300: '#F2B544',
          400: '#E5A02E', 500: '#D98C1F', 600: '#A96D15', 700: '#7A4E0E',
          800: '#4B2F08', 900: '#1F1403',
          DEFAULT: 'var(--color-accent)',
        },
        danger: {
          50: '#FBE9EA', 100: '#F5C8CB', 200: '#EB9197', 300: '#E56B75',
          400: '#E5484D', 500: '#B3261E', 600: '#8E1C16', 700: '#6A1410',
          800: '#450D0A', 900: '#220605',
          DEFAULT: 'var(--color-danger)',
        },
        surface: {
          DEFAULT: 'var(--color-surface)',
          raised: 'var(--color-surface-raised)',
          overlay: 'var(--color-surface-overlay)',
        },
        text: {
          DEFAULT: 'var(--color-text)',
          muted: 'var(--color-text-muted)',
        },
      },
      backgroundImage: {
        'gradient-hero': 'var(--gradient-hero)',
        'gradient-calm': 'var(--gradient-calm)',
        'gradient-emergency': 'var(--gradient-emergency)',
        'gradient-surface': 'var(--gradient-surface)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '25%': { transform: 'translateX(-4px)' },
          '75%': { transform: 'translateX(4px)' },
        },
      },
    },
  },
  plugins: [],
}
