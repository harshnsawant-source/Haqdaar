import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // The engine runs locally on 8000. Proxying keeps the PWA same-origin, so the
  // service worker sees API calls it is allowed to cache — a cross-origin fetch would
  // be opaque to it and the offline story would quietly not work.
  //
  // `preview` needs its own entry: vite does NOT apply `server.proxy` to the preview
  // server, and preview is what actually exercises the service worker, because the
  // worker only registers in production builds.
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  preview: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
