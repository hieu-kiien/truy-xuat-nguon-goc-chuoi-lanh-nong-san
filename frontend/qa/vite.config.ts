import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  define: { 'import.meta.env.VITE_ENABLE_DEMO_LOGIN': JSON.stringify('true') },
  build: { outDir: 'dist-preview', rolldownOptions: { input: 'preview.html' } },
})
