import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/get_attribute_trees': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        ws: true,
      },
      '/reset_session': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/get_history': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    }
  }
})
