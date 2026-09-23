/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cat: {
          yellow: '#FFCD11',
          gold: '#E5B600',
          amber: '#F59E0B',
          dark: '#121316',
          panel: '#1A1D21',
          card: '#22262C',
          border: '#2E343D',
          hover: '#2D333B',
          danger: '#EF4444',
          success: '#10B981',
          cyan: '#06B6D4',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Menlo', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'cat': '0 4px 20px -2px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(255, 205, 17, 0.15)',
        'cat-glow': '0 0 25px rgba(255, 205, 17, 0.25)',
        'danger-glow': '0 0 25px rgba(239, 68, 68, 0.4)',
      },
      keyframes: {
        hazard: {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '40px 0' },
        },
        pulseAlert: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        }
      },
      animation: {
        'hazard-stripe': 'hazard 2s linear infinite',
        'pulse-alert': 'pulseAlert 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
