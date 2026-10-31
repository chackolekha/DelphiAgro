/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        leaf: { 50: "#f0fdf4", 600: "#16a34a", 700: "#15803d" },
      },
    },
  },
  plugins: [],
};
