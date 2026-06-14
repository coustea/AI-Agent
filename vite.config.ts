import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9999',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:9999',
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

          if (id.includes('element-plus') || id.includes('@element-plus')) {
            return 'vendor-element'
          }

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
})
