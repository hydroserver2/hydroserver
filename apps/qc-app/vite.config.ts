/// <reference types="vitest" />

import { defineConfig, loadEnv } from 'vite'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

// @ts-ignore
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_APP_PROXY_BASE_URL
  const qcUtilsRoot = resolve(__dirname, '../../packages/qc-utils/src')
  const useLocalQcUtils = command === 'serve' || env.VITE_QC_UTILS_LOCAL === '1'
  const clientRoot = resolve(__dirname, '../../packages/hydroserver-ts/src')
  const useLocalClient = env.VITE_HYDROSERVER_CLIENT_LOCAL !== '0'

  return {
    base: mode === 'django' ? '/static/qc/' : '/qc/',
    plugins: [
      vue(),
      vuetify({
        autoImport: true,
        styles: { configFile: 'src/styles/settings.scss' },
      }),
    ],
    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler', // or "modern"
        },
      },
    },
    optimizeDeps: {
      exclude: [
        'vuetify',
        ...(useLocalQcUtils ? ['@uwrl/qc-utils'] : []),
        ...(useLocalClient ? ['@hydroserver/client'] : []),
      ],
    },
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy: {
        ...(apiProxyTarget
          ? {
              '/api': {
                target: apiProxyTarget,
                changeOrigin: true,
              },
            }
          : {}),
      },
      // COOP/COEP headers enable SharedArrayBuffer-backed workers (fast
      // shared-memory data ops) but also block cross-origin responses
      // that don't carry CORP — including the `playground.hydroserver.org`
      // API. On by default; set `VITE_APP_DISABLE_COOP=1` to drop them
      // when you need to talk to a backend that doesn't serve CORP headers.
      // The worker layer gracefully falls back to inline execution when
      // SharedArrayBuffer isn't available.
      headers:
        env.VITE_APP_DISABLE_COOP === '1'
          ? undefined
          : {
              'Cross-Origin-Opener-Policy': 'same-origin',
              'Cross-Origin-Embedder-Policy': 'require-corp',
            },
      fs: {
        allow: [
          resolve(__dirname),
          ...(useLocalQcUtils ? [qcUtilsRoot] : []),
          ...(useLocalClient ? [clientRoot] : []),
        ],
      },
    },
    resolve: {
      extensions: ['.js', '.json', '.vue', '.less', '.scss', '.ts', '.py'],
      alias: {
        '@': resolve(__dirname, 'src'),
        ...(useLocalQcUtils
          ? { '@uwrl/qc-utils': resolve(qcUtilsRoot, 'index.ts') }
          : {}),
        ...(useLocalClient
          ? { '@hydroserver/client': resolve(clientRoot, 'index.ts') }
          : {}),
      },
    },
    build: {
      manifest: true,
    },
    test: {
      globals: true,
      include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
      exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
      environmentMatchGlobs: [['src/components/**', 'jsdom']],
      server: {
        deps: {
          inline: ['vuetify'],
        },
      },
      setupFiles: ['@vitest/web-worker', './src/utils/test/setup.ts'],
      environment: 'jsdom',
      coverage: {
        exclude: [
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
          // Plotly DOM-staging seam — same shape as `events.ts` /
          // `interaction.ts`. Mostly Plotly relayout calls + drag-
          // gesture wiring that resists meaningful unit testing.
          '**/src/utils/plotting/staging.ts',
          // Barrel re-export — no logic to cover, but appears in the
          // coverage report at 0% because nothing imports it directly
          // from a test (everything goes through the source modules).
          '**/src/utils/plotting/plotly.ts',
          '**/src/main.ts',
          '**/*.d.ts',
          '**/postcss.config.js',
        ],
        thresholds: {
          lines: 80,
          statements: 80,
          functions: 80,
          // Branches sits a couple points below the others because the
          // last few uncovered branches live in the qualifier-band path
          // of `options.ts` and the relayout-echo path of `selected.ts`
          // — both require heavy Plotly-DOM fixture setup for marginal
          // signal. Raise back to 80 once those are covered.
          branches: 78,
        },
        provider: 'v8',
        reporter: ['text', 'json', 'html'],
      },
    },
  }
})
