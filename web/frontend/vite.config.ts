import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const port = env.VITE_PORT || '5002'
  
  return {
    plugins: [react()],
    server: {
      proxy: {
        '/get_attribute_trees': {
          target: `http://localhost:${port}`,
          changeOrigin: true,
        },
        '/socket.io': {
          target: `http://localhost:${port}`,
          changeOrigin: true,
          ws: true,
        },
        '/reset_session': {
          target: `http://localhost:${port}`,
          changeOrigin: true,
        },
        '/get_history': {
          target: `http://localhost:${port}`,
          changeOrigin: true,
        },
        '/get_logs': {
          target: `http://localhost:${port}`,
          changeOrigin: true,
        }
      }
    }
  }
})
