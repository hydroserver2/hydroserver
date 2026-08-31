import { defineConfig, loadEnv } from 'vite'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const useLocal = env.VITE_HYDROSERVER_CLIENT_LOCAL !== '0'
  const sdkRoot = resolve(
    __dirname,
    env.VITE_HYDROSERVER_CLIENT_PATH || '../../packages/hydroserver-ts/src'
  )
  const sdkEntry = resolve(sdkRoot, 'index.ts')

  return {
    server: {
      host: '127.0.0.1',
      port: 5001,
      strictPort: true,
      fs: {
        allow: [sdkRoot, resolve(__dirname)],
      },
    },
    optimizeDeps: {
      exclude: useLocal ? ['@hydroserver/client'] : [],
    },
    resolve: {
      alias: {
        ...(useLocal ? { '@hydroserver/client': sdkEntry } : {}),
      },
    },
  }
})