import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-server proxy mirrors what nginx does in production (docker-compose.yml):
// same-origin paths /api and /agent, forwarded to the two backend services.
// This means the frontend code never needs to know the difference between
// `npm run dev` and the containerized build.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/agent': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agent/, ''),
      },
    },
  },
})
