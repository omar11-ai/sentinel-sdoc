import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    outDir: '../static/app',
    emptyOutDir: true,
    /* esbuild keeps `backdrop-filter: url(#…)` verbatim; the default
       lightningcss minifier rewrites it to -webkit-only and Chrome drops it */
    cssMinify: 'esbuild',
  },
})
