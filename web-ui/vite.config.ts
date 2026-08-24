import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // The websocket entry must come first: keys are matched in order and
      // '/api' would otherwise swallow '/api/ws' as a plain HTTP proxy.
      '/api/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      '/api': 'http://localhost:8000',
    },
  },
})
