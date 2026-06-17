import { defineConfig, loadEnv } from 'vite'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import vuetify from 'vite-plugin-vuetify'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_APP_PROXY_BASE_URL
  const qcProxyTarget = env.VITE_APP_QC_PROXY_BASE_URL || 'http://127.0.0.1:5173'
  const useLocal = env.VITE_HYDROSERVER_CLIENT_LOCAL !== '0'
  const sdkRoot = resolve(
    __dirname,
    env.VITE_HYDROSERVER_CLIENT_PATH || '../../packages/hydroserver-ts/src'
  )
  const sdkEntry = resolve(sdkRoot, 'index.ts')
  console.log('[SDK alias active?]', useLocal, sdkEntry)

  return {
    base: mode === 'django' ? '/static/web/' : '/',
    plugins: [
      vue(),
      tailwindcss(),
      vuetify({
        autoImport: true,
        styles: { configFile: 'src/styles/settings.scss' },
      }),
    ],
    optimizeDeps: {
      exclude: ['vuetify', ...(useLocal ? ['@hydroserver/client'] : [])],
    },
    server: {
      host: '127.0.0.1',
      port: 1203,
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
        '/qc': {
          target: qcProxyTarget,
          changeOrigin: true,
          ws: true,
        },
      },
      fs: {
        allow: [
          sdkRoot,
          resolve(__dirname), // <- add this
        ],
      },
    },
    resolve: {
      extensions: ['.js', '.json', '.vue', '.less', '.scss', '.ts'],
      alias: {
        '@': resolve(__dirname, 'src'),
        ...(useLocal ? { '@hydroserver/client': sdkEntry } : {}),
      },
    },
    build: {
      manifest: true,
    },
    test: {
      globals: true,
      environmentMatchGlobs: [['src/components/**', 'jsdom']],
      setupFiles: ['src/test/setup.ts'],
      server: {
        deps: {
          inline: ['vuetify'],
        },
      },
      environment: 'jsdom',
      coverage: {
        include: ['src/**/*.{ts,tsx,js,jsx}'],
        exclude: [
          '**/src/composables/useWorkspaceTags.ts',
          '**/src/composables/useHydroShare.ts',
          '**/src/composables/useWorkspacePermissions.ts',
          '**/src/composables/useMetadata.ts',
          '**/src/composables/useVocabulary.ts',
          '**/src/composables/useSystemTableLogic.ts',
          '**/src/composables/orchestration/useSimpleTaskDetails.ts',
          '**/src/composables/orchestration/useTaskRunNowPolling.ts',
          '**/src/services/getCSRFToken.ts',
          '**/src/models/**',
          '**/src/plugins/**',
          '**/src/router/**',
          '**/src/store/**',
          '**/src/types/**',
          '**/src/config/**',
          '**/src/services/apiMethods.ts',
          '**/src/services/handle401.ts',
          '**/src/utils/materialColors.ts',
          '**/src/utils/CSVDownloadUtils.ts',
          '**/src/utils/plotting/plotly.ts',
          '**/src/utils/plotting/graphSeriesUtils.ts',
          '**/src/utils/test/**',
          '**/src/utils/time.ts',
          '**/src/utils/googleMaps/**',
          '**/src/utils/maps/**',
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
