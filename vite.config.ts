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
      // COOP/COEP headers enable SharedArrayBuffer-backed workers (fast
      // shared-memory data ops) but also block cross-origin responses
      // that don't carry CORP — including the `playground.hydroserver.org`
      // API. On by default; set `VITE_APP_DISABLE_COOP=1` to drop them
      // when you need to talk to a backend that doesn't serve CORP headers.
      // The worker layer gracefully falls back to inline execution when
      // SharedArrayBuffer isn't available.
      headers: env.VITE_APP_DISABLE_COOP === '1'
        ? undefined
        : {
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
      exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
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
          // Phase 02: individual opt-in for stores + three SFCs; blanket excludes removed.
          // Untested stores stay excluded until covered by a future phase
          '**/src/store/observations.ts',
          '**/src/store/hydroserver.ts',
          '**/src/store/user.ts',
          // Only EditHistory.vue, DataTable.vue, DatastreamFilters.vue are unit-tested; all others excluded
          '**/src/App.vue',
          '**/src/components/VisualizeData.vue',
          '**/src/components/EditData/AddPoints.vue',
          '**/src/components/EditData/ChangeValues.vue',
          '**/src/components/EditData/DeletePoints.vue',
          '**/src/components/EditData/DriftCorrection.vue',
          '**/src/components/EditData/FillGaps.vue',
          '**/src/components/EditData/Interpolate.vue',
          '**/src/components/EditData/OperationPanel.vue',
          '**/src/components/EditData/QualifyingComments.vue',
          '**/src/components/EditData/ShiftDatetimes.vue',
          '**/src/components/FilterPoints/**/*.vue',
          '**/src/components/Navigation/**/*.vue',
          '**/src/components/VisualizeData/DataVisDatasetsTable.vue',
          '**/src/components/VisualizeData/DataVisTimeFilters.vue',
          '**/src/components/VisualizeData/DataVisualization.vue',
          '**/src/components/VisualizeData/DatastreamInformationCard.vue',
          '**/src/components/VisualizeData/DatePickerField.vue',
          '**/src/components/VisualizeData/EditableCell.vue',
          '**/src/components/VisualizeData/FilterPanel.vue',
          '**/src/components/VisualizeData/Plot.vue',
          '**/src/components/VisualizeData/PlottedDatastreams.vue',
          '**/src/components/VisualizeData/SeriesStyleCard.vue',
          '**/src/components/account/**/*.vue',
          '**/src/components/base/**/*.vue',
          '**/src/pages/**/*.vue',
          '**/src/plugins/**',
          '**/src/router/**',
          '**/src/types/**',
          '**/src/config/**',
          '**/src/utils/mdi-icons.ts',
          '**/src/utils/observations.ts',
          '**/src/utils/test/**',
          '**/src/utils/rules.ts',
          '**/src/utils/plotting/events.ts',
          '**/src/utils/plotting/interaction.ts',
          '**/src/utils/plotting/operations.ts',
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
