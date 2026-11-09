import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:9999'

  return {
    plugins: [
      vue(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
        '/static': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
      watch: {
        ignored: ['**/server/**'],
      },
    },
    worker: {
      format: 'es',
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return

            if (id.includes('echarts') || id.includes('vue-echarts')) {
              return 'vendor-charts'
            }

            if (
              id.includes('markmap') ||
              id.includes('shiki') ||
              id.includes('@shikijs') ||
              id.includes('katex') ||
              id.includes('remark-') ||
              id.includes('rehype-') ||
              id.includes('unified')
            ) {
              return 'vendor-renderers'
            }

            if (id.includes('monaco-editor')) {
              return 'vendor-monaco'
            }

            return 'vendor'
          },
        },
      },
    },
  }
})
