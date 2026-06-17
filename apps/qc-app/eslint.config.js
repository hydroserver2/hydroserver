import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import vue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'

// Flat config for the QC App. Sits alongside Prettier (formatting) and
// `vue-tsc` (type-check). ESLint catches the runtime-correctness gaps
// that the type-checker doesn't (unused vars, floating promises,
// unused expressions), plus a thin set of Vue-template hygiene rules.
export default [
  {
    ignores: [
      'dist/**',
      'coverage/**',
      'node_modules/**',
      'playwright-report/**',
      'test-results/**',
      '*.config.js',
      '*.config.ts',
      '*.config.mjs',
      '*.config.cjs',
      'env.d.ts',
    ],
  },

  // TS / JS source.
  {
    files: ['src/**/*.{ts,js}', 'e2e/**/*.ts'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: 2023,
        sourceType: 'module',
      },
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        requestAnimationFrame: 'readonly',
        cancelAnimationFrame: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        navigator: 'readonly',
        fetch: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        Worker: 'readonly',
        Promise: 'readonly',
        Map: 'readonly',
        Set: 'readonly',
        Symbol: 'readonly',
        HTMLElement: 'readonly',
        Element: 'readonly',
        Event: 'readonly',
        MouseEvent: 'readonly',
        KeyboardEvent: 'readonly',
        WheelEvent: 'readonly',
        process: 'readonly',
      },
    },
    plugins: {
      '@typescript-eslint': tseslint.plugin,
    },
    rules: {
      ...js.configs.recommended.rules,
      // The strict typescript-eslint rules require type info via project
      // service; keep to the syntactic rules so `npm run lint` doesn't
      // need a separate parse pass of the whole repo.
      ...tseslint.configs.recommended[1].rules,

      // `no-unused-vars` would double-fire with the TS variant; use the
      // TS-aware one only.
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],

      // Mute the rules whose ergonomics don't match the codebase.
      // `any` is sometimes the right escape hatch around Plotly's typings
      // and the existing inline `as any` casts. Promote to `warn` later
      // once the type surface has been tightened.
      '@typescript-eslint/no-explicit-any': 'off',
      // The runtime parts of the app intentionally use `Function` in a
      // few places (debounce wrappers, plugin contracts).
      '@typescript-eslint/no-unsafe-function-type': 'off',
      // Empty interfaces are used as extension points for shared shapes.
      '@typescript-eslint/no-empty-object-type': 'off',
      // `@ts-ignore` shows up in `vite.config.ts` and qc-utils consumers;
      // demoting to warn keeps it visible without blocking CI.
      '@typescript-eslint/ban-ts-comment': 'warn',

      'no-empty': 'warn',
      'no-prototype-builtins': 'warn',
      'no-useless-escape': 'warn',
    },
  },

  // Vue SFCs.
  ...vue.configs['flat/recommended'],
  {
    files: ['src/**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 2023,
        sourceType: 'module',
        extraFileExtensions: ['.vue'],
      },
    },
    rules: {
      // Multi-word component names are not enforced because most of
      // the SFC tree is page / panel components named after the
      // domain concept (`EditHistory`, `DataTable`, `FilterPanel`).
      'vue/multi-word-component-names': 'off',
      // The codebase uses both `<template>` ordering conventions
      // (template before script and vice versa). Pick neither.
      'vue/component-tags-order': 'off',
      'vue/block-order': 'off',
      // Vuetify components take a lot of long-form props; the default
      // max-attributes-per-line is too strict for them.
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/html-indent': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/attributes-order': 'off',
    },
  },

  // Test files: relax the rules that get noisy in fixtures + describe
  // blocks (intentionally unused destructured fields, etc).
  {
    files: ['src/**/__tests__/**/*.{ts,js}', 'e2e/**/*.ts'],
    rules: {
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },
]
