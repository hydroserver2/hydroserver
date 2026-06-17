import { resolve } from "path";
import { defineConfig } from "vite";
// import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig(({ mode }) => {
  const isProd = mode === "prod";
  const isDev = mode === "dev";

  let build = {};
  if (isProd) {
    build = {
      lib: {
        entry: resolve(__dirname, "src/index.ts"),
        name: "@uwrl/qc-utils",
        fileName: "index",
      },
      // sourcemap: true,
      rollupOptions: {
        /**
         * DESC:
         * make sure to externalize deps that shouldn't be bundled
         * into your library
         */
        output: {
          /**
           * DESC:
           * Provide global variables to use in the UMD build
           * for externalized deps
           */
          globals: {
            // vue: 'Vue',
            // vuetify: 'Vuetify',
            // 'vue-facing-decorator': 'vueFacingDecorator',
          },
        },
      },
    };
  }

  if (isDev) {
    /**
     * DESC:
     * dependency pre-bundling
     */
  }

  const test = {
    globals: true,
    environment: "happy-dom",
    include: ["src/**/__tests__/*.spec.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "text-summary", "lcov"],
      thresholds: {
        lines: 80,
        statements: 80,
        functions: 80,
        branches: 80,
      },
      exclude: [
        "dist/**",
        "node_modules/**",
        "**/*.d.ts",
        "src/index.ts",
        "src/types/**", // type definitions — not executable code
        "**/__tests__/**",
        "**/*.worker.ts",
      ],
    },
  };

  return {
    // plugins: [
    //   visualizer(),
    // ],
    // optimizeDeps,
    build,
    test,

    /**
     * DESC:
     * defining aliases
     */
    resolve: {
      alias: [
        {
          find: "@",
          replacement: resolve(__dirname, "./src"),
        },
      ],
    },
  };
});
