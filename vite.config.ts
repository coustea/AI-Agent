import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:9999'
  const wsProxyTarget = env.VITE_WS_PROXY_TARGET || apiProxyTarget.replace(/^http/, 'ws')

  return {
    plugins: [vue(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@ppt-manifest': fileURLToPath(new URL('./server/app/resource/templates/ppt_manifest.json', import.meta.url)),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: wsProxyTarget,
          ws: true,
          changeOrigin: true,
        },
      },
      watch: {
        ignored: ['**/server/**'],
      },
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
              id.includes('katex') ||
              id.includes('markdown-it') ||
              id.includes('highlight.js')
            ) {
              return 'vendor-renderers'
            }

            return 'vendor'
          },
        },
      },
    },
  }
})
