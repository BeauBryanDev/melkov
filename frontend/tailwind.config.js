/**
 * Tailwind, configured to sit *alongside* the hand-written palace CSS rather
 * than replace it.
 *
 * Two decisions matter here:
 *
 * - `preflight: false`. Tailwind's base reset rewrites margins, borders,
 *   heading sizes and form styles across the whole document. Enabling it
 *   would flatten the existing desktop design, which is approved and must
 *   not regress. With preflight off, Tailwind contributes *only* the utility
 *   classes actually used in the markup — purely additive.
 *
 * - Only `@tailwind utilities` is imported (see styles.css), and it sits at
 *   the end of the file. Utilities and the existing `.panel`-style classes
 *   have the same specificity, so source order decides: utilities placed
 *   last win, which is what makes a responsive override like `max-lg:hidden`
 *   able to beat a base rule.
 *
 * The theme mirrors the CSS custom properties so utilities and hand-written
 * rules draw from one palette.
 *
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        deep: "var(--bg-deep)",
        royal: "var(--royal)",
        elevated: "var(--elevated)",
        gold: {
          high: "var(--gold-high)",
          DEFAULT: "var(--gold)",
          deep: "var(--gold-deep)",
        },
        ivory: "var(--text)",
        muted: "var(--muted)",
      },
      fontFamily: {
        display: ["Cinzel", "Georgia", "serif"],
        body: ["EB Garamond", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
    },
    screens: {
      xs: "400px",
      sm: "560px",
      md: "760px",
      lg: "1024px",
      xl: "1180px",
      "2xl": "1440px",
    },
  },
  plugins: [],
};
