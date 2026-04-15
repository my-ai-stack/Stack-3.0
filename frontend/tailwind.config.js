/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        void: '#050505',
        surface: '#0A0A0A',
        'electric-purple': '#B026FF',
        'cyber-cyan': '#00F0FF',
      },
      borderColor: {
        stitch: 'rgba(255, 255, 255, 0.1)',
      },
      backgroundImage: {
        'neon-gradient': 'linear-gradient(90deg, #60a5fa, #a855f7)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
