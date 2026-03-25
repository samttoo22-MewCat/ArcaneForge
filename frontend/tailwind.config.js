/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        cinzel: ["Cinzel", "serif"],
        inter: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        void: "#0C0A09",
        stone: {
          950: "#161412",
          900: "#201D1A",
          800: "#2C2825",
          700: "#3A3530",
          600: "#524A44",
          500: "#8A8078",
          400: "#B0A89E",
          300: "#CEC6BC",
          200: "#E0D8CE",
          100: "#F4EFE8",
        },
        gold: {
          DEFAULT: "#D4A030",
          light: "#F0C060",
          dark: "#9A7018",
          glow: "rgba(212,160,48,0.35)",
        },
        ember: {
          DEFAULT: "#E07820",
          light: "#F89030",
        },
        hp: {
          DEFAULT: "#C83838",
          bright: "#F05050",
          glow: "rgba(200,56,56,0.4)",
        },
        mp: {
          DEFAULT: "#3070B8",
          bright: "#60A8E8",
          glow: "rgba(48,112,184,0.4)",
        },
        xp: {
          DEFAULT: "#30983A",
          bright: "#50D460",
        },
      },
      boxShadow: {
        gold: "0 0 20px rgba(212,160,48,0.45), 0 0 40px rgba(212,160,48,0.18)",
        "gold-sm": "0 0 10px rgba(212,160,48,0.6)",
        hp: "0 0 14px rgba(200,56,56,0.55)",
        mp: "0 0 14px rgba(48,112,184,0.55)",
        panel: "inset 0 1px 0 rgba(255,255,255,0.06), 0 2px 12px rgba(0,0,0,0.5)",
      },
      keyframes: {
        "pulse-gold": {
          "0%, 100%": { opacity: "1", filter: "drop-shadow(0 0 7px rgba(212,160,48,0.9))" },
          "50%": { opacity: "0.75", filter: "drop-shadow(0 0 14px rgba(212,160,48,1))" },
        },
        "glow-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "travel-pulse": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "pulse-gold": "pulse-gold 2s ease-in-out infinite",
        "glow-in": "glow-in 0.25s ease forwards",
        "travel-pulse": "travel-pulse 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
