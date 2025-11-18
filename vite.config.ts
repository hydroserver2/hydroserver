/// <reference types="vitest" />

import { defineConfig, loadEnv } from 'vite'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

// @ts-ignore
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  const base = env.VITE_APP_ROUTE || '/'

  return {
    base,
    plugins: [
      vue(),
      vuetify({
        autoImport: true,
        styles: { configFile: 'src/styles/settings.scss' },
      }),
    ],
    define: {
      VITE_APP_VERSION: JSON.stringify(process.env.npm_package_version),
    },
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler', // or "modern"
        },
      },
    },
    optimizeDeps: {
      exclude: ['vuetify'],
    },
    server: {
      host: '127.0.0.1',
      port: 1203,
      strictPort: true,
      // These headers are required to enable workers
      // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer#security_requirements
      headers: {
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Embedder-Policy': 'require-corp',
      },
    },
    resolve: {
      extensions: ['.js', '.json', '.vue', '.less', '.scss', '.ts', '.py'],
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    build: {
      manifest: true,
    },
    test: {
      globals: true,
      environmentMatchGlobs: [['src/components/**', 'jsdom']],
      server: {
        deps: {
          inline: ['vuetify'],
        },
      },
      setupFiles: ['@vitest/web-worker'],
      environment: 'jsdom',
      coverage: {
        exclude: [
          '**/src/**/*.vue',
          '**/src/plugins/**',
          '**/src/router/**',
          '**/src/store/**',
          '**/src/types/**',
          '**/src/config/**',
          '**/src/utils/mdi-icons.ts',
          '**/src/utils/observations.ts',
          '**/src/utils/test/**',
          '**/src/utils/rules.ts',
          '**/src/App.vue',
          '**/src/main.ts',
          '**/*.d.ts',
          '**/postcss.config.js',
        ],
        thresholds: {
          lines: 80,
          statements: 80,
          functions: 80,
          branches: 80,
        },
        provider: 'v8',
        reporter: ['text', 'json', 'html'],
      },
    },
  }
})
