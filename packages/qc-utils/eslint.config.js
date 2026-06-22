import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default [
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "coverage/**",
      "*.config.js",
      "*.config.ts",
      "*.config.mjs",
      "*.config.cjs",
      "stats.html",
    ],
  },
  {
    files: ["src/**/*.{ts,js}"],
    languageOptions: {
      parser: tseslint.parser,
      ecmaVersion: 2023,
      sourceType: "module",
      globals: {
        // Node + browser globals — qc-utils is a library consumed in browser apps.
        process: "readonly",
        console: "readonly",
        document: "readonly",
        window: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        Worker: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        Promise: "readonly",
        Map: "readonly",
        Set: "readonly",
        Symbol: "readonly",
        Buffer: "readonly",
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": "warn",
      "no-undef": "warn",
      "no-empty": "warn",
      "no-prototype-builtins": "warn",
      "no-useless-escape": "warn",
    },
  },

  // Test files: relax the rules that get noisy in fixtures + describe
  // blocks (intentionally unused destructured fields, `vi.mock` factory
  // args, etc.). Mirrors the matching block in `hydroserver-qc-app`.
  {
    files: ["src/**/__tests__/**/*.{ts,js}"],
    rules: {
      "no-unused-vars": "off",
    },
  },
];
