import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18086',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:18086',
        changeOrigin: true,
      },
      '/metrics': {
        target: 'http://127.0.0.1:18086',
        changeOrigin: true,
      },
      '/system-health': {
        target: 'http://127.0.0.1:18090',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/system-health/, '/health'),
      },
      '/events-api': {
        target: 'http://127.0.0.1:18085',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/events-api/, '/v1'),
        headers: {
          Authorization: 'Bearer admin-key-secret',
        },
      },
      '/gateway-api': {
        target: 'http://127.0.0.1:18080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/gateway-api/, '/v1'),
        headers: {
          Authorization: 'Bearer key-tenant-cisco-prod',
        },
      },
      '/m2-api': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/m2-api/, '/v1'),
        headers: {
          Authorization: 'Bearer system-admin-token',
        },
      },
    },
  },
  build: { outDir: 'dist', sourcemap: true },
})
