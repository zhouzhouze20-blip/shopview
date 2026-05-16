import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

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
  // 移除硬编码的API URL，让前端根据域名自动判断
  // define: {
  //   'import.meta.env.VITE_API_URL': JSON.stringify('http://192.168.98.81:7000')
  // }
})
