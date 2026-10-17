import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { apiPort, webPort } from './ports'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: webPort,
    strictPort: true,
    proxy: { '/api': { target: `http://127.0.0.1:${apiPort}`, ws: true } },
  },
  build: { rollupOptions: { output: { manualChunks: { charts: ['echarts'] } } } },
})
