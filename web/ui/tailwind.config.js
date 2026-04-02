/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        shadow: {
          900: '#0d1117',
          800: '#161b22',
          700: '#21262d',
          600: '#30363d',
          500: '#484f58',
          400: '#6e7681',
          300: '#8b949e',
          200: '#c9d1d9',
          100: '#f0f6fc',
        },
        accent: {
          blue: '#58a6ff',
          green: '#3fb950',
          yellow: '#d29922',
          orange: '#f78166',
          red: '#f85149',
          purple: '#a371f7',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(88, 166, 255, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(88, 166, 255, 0.8)' },
        }
      }
    },
  },
  plugins: [],
}