import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    // Build straight into the Python package so the wheel can ship the UI.
    outDir: '../yoink/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8090',
      '/ws': { target: 'ws://127.0.0.1:8090', ws: true },
    },
  },
})
