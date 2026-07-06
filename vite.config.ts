import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import monacoEditorPluginModule from 'vite-plugin-monaco-editor'
import { fileURLToPath, URL } from 'node:url'

// Handle CJS dual-default export from vite-plugin-monaco-editor
const monacoEditorPlugin = (monacoEditorPluginModule as any).default || monacoEditorPluginModule

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:9999'
  const wsProxyTarget = env.VITE_WS_PROXY_TARGET || apiProxyTarget.replace(/^http/, 'ws')

  return {
    plugins: [
      vue(),
      tailwindcss(),
      monacoEditorPlugin({}),
    ],
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
