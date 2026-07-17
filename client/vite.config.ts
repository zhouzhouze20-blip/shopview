import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'
const versionFile = [
  path.resolve(__dirname, '../VERSION'),
  path.resolve(__dirname, 'VERSION'),
].find((candidate) => fs.existsSync(candidate))
const appVersion = versionFile
  ? fs.readFileSync(versionFile, 'utf8').trim()
  : '1.0.0'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    host: true,
    strictPort: true, // 如果端口被占用，不自动切换到其他端口
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    exclude: ['@uppy/aws-s3', '@uppy/core', '@uppy/dashboard']
  },
  build: {
    target: 'es2020',
    outDir: 'dist',
    assetsDir: 'assets',
    base: '/static/'
  },
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
  },
})
