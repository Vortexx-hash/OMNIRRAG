/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        deep: '#04040d',
        surface: '#0a0a18',
        card: '#0f0f20',
        hover: '#141428',
      },
      boxShadow: {
        'glow-violet': '0 0 24px rgba(139, 92, 246, 0.35)',
        'glow-cyan': '0 0 24px rgba(6, 182, 212, 0.35)',
        'glow-green': '0 0 24px rgba(16, 185, 129, 0.35)',
        'glow-amber': '0 0 24px rgba(245, 158, 11, 0.35)',
        'glow-red': '0 0 24px rgba(239, 68, 68, 0.35)',
        'glow-sm': '0 0 10px rgba(139, 92, 246, 0.2)',
        'glow-lg': '0 0 50px rgba(139, 92, 246, 0.5)',
      },
      backgroundImage: {
        'neural': 'radial-gradient(ellipse at 25% 25%, rgba(139,92,246,0.12) 0%, transparent 55%), radial-gradient(ellipse at 75% 75%, rgba(6,182,212,0.08) 0%, transparent 55%)',
        'gradient-violet': 'linear-gradient(135deg, #7C3AED, #8B5CF6)',
        'gradient-cyan': 'linear-gradient(135deg, #0891B2, #06B6D4)',
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2.5s linear infinite',
        'spin-slow': 'spin 6s linear infinite',
        'draw-in': 'drawIn 0.8s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
        'fade-in': 'fadeIn 0.4s ease-out forwards',
        'scale-in': 'scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 10px rgba(139,92,246,0.2)' },
          '50%': { boxShadow: '0 0 35px rgba(139,92,246,0.6)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        drawIn: {
          '0%': { strokeDashoffset: '500', opacity: '0' },
          '100%': { strokeDashoffset: '0', opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
