import { defineConfig } from 'vite'

export default defineConfig({
  build: {
    lib: {
      entry: 'src/index.ts',
      name: '@hydroserver-client',
      fileName: '@hydroserver-client',
      formats: ['es', 'umd'],
    },
    sourcemap: true,
    rollupOptions: {
      output: {
        exports: 'named',
      },
      external: [], // add externals to keep them out of your bundle if needed
    },
  },
})
