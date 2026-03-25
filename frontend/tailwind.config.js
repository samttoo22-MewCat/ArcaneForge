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
        // 更暗更冷：帶藍色調的石牆底色
        void: "#040608",
        stone: {
          950: "#090C12",
          900: "#111520",
          800: "#1A202E",
          700: "#252E3E",
          600: "#374455",
          500: "#5A6E82",
          400: "#8EA0B4",
          300: "#B0C0D0",
          200: "#C8D4E0",
          100: "#E0E8F0",
        },
        forest: {
          DEFAULT: "#2E7048",
          light: "#4A9E60",
          bright: "#64C07A",
          dark: "#1E4A30",
          glow: "rgba(74,158,96,0.45)",
        },
        gold: {
          DEFAULT: "#C89030",
          light: "#E8B050",
          dark: "#886010",
          glow: "rgba(200,144,48,0.35)",
        },
        ember: {
          DEFAULT: "#D06820",
          light: "#F08040",
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
        forest: "0 0 18px rgba(74,158,96,0.55), 0 0 36px rgba(74,158,96,0.2)",
        "forest-sm": "0 0 10px rgba(74,158,96,0.75)",
        gold: "0 0 20px rgba(200,144,48,0.4), 0 0 40px rgba(200,144,48,0.15)",
        hp: "0 0 14px rgba(200,56,56,0.55)",
        mp: "0 0 14px rgba(48,112,184,0.55)",
        panel: "inset 0 1px 0 rgba(255,255,255,0.04), 0 2px 12px rgba(0,0,0,0.6)",
      },
      keyframes: {
        "pulse-forest": {
          "0%, 100%": { opacity: "1", filter: "drop-shadow(0 0 6px rgba(74,158,96,0.8))" },
          "50%": { opacity: "0.7", filter: "drop-shadow(0 0 14px rgba(74,158,96,1))" },
        },
        "pulse-gold": {
          "0%, 100%": { opacity: "1", filter: "drop-shadow(0 0 7px rgba(200,144,48,0.9))" },
          "50%": { opacity: "0.75", filter: "drop-shadow(0 0 14px rgba(200,144,48,1))" },
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
        "pulse-forest": "pulse-forest 2.5s ease-in-out infinite",
        "pulse-gold": "pulse-gold 2s ease-in-out infinite",
        "glow-in": "glow-in 0.25s ease forwards",
        "travel-pulse": "travel-pulse 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
