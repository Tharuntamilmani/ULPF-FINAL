import { defineConfig, createLogger } from 'vite'
import react from '@vitejs/plugin-react'

// Suppress proxy ECONNREFUSED terminal noise when backend microservices are offline
const customLogger = createLogger()
const loggerError = customLogger.error.bind(customLogger)
customLogger.error = (msg, options) => {
  if (typeof msg === 'string' && msg.includes('http proxy error')) {
    return
  }
  loggerError(msg, options)
}

const handleProxyError = (proxy: any) => {
  proxy.on('error', (_err: any, _req: any, res: any) => {
    if (res && typeof res.writeHead === 'function' && !res.headersSent) {
      res.writeHead(503, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({
        status: 'UNAVAILABLE',
        error: 'Backend microservices are currently offline. Running in Demo Simulation mode.',
        code: 'ECONNREFUSED',
      }))
    }
  })
}

export default defineConfig({
  customLogger,
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18086',
        changeOrigin: true,
        configure: handleProxyError,
      },
      '/health': {
        target: 'http://127.0.0.1:18086',
        changeOrigin: true,
        configure: handleProxyError,
      },
      '/metrics': {
        target: 'http://127.0.0.1:18086',
        changeOrigin: true,
        configure: handleProxyError,
      },
      '/system-health': {
        target: 'http://127.0.0.1:18090',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/system-health/, '/health'),
        configure: handleProxyError,
      },
      '/events-api': {
        target: 'http://127.0.0.1:18085',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/events-api/, '/v1'),
        headers: {
          Authorization: 'Bearer admin-key-secret',
        },
        configure: handleProxyError,
      },
      '/gateway-api': {
        target: 'http://127.0.0.1:18080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/gateway-api/, '/v1'),
        headers: {
          Authorization: 'Bearer key-tenant-cisco-prod',
        },
        configure: handleProxyError,
      },
      '/m2-api': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/m2-api/, '/v1'),
        headers: {
          Authorization: 'Bearer system-admin-token',
        },
        configure: handleProxyError,
      },
    },
  },
  build: { outDir: 'dist', sourcemap: true },
})
