import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend URL: defaults to localhost for local dev.
// Set VITE_BACKEND_URL=http://100.x.x.x:8000 to point to Kaggle GPU.
const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://localhost:8000'
const RENDER_URL = process.env.VITE_RENDER_URL || 'http://localhost:3100'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: [
      'openshorts.app',
      'www.openshorts.app'
    ],
    proxy: {
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/videos': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/thumbnails': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/gallery': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/video': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/render': {
        target: RENDER_URL,
        changeOrigin: true,
      }
    }
  }
})
