// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { // <--- Add this server section
    proxy: {
      // string shorthand for simple proxy rules
      '/notes': 'http://localhost:8000',
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  esbuild: {
    target: 'es2020'
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'es2020'
    }
  }
})