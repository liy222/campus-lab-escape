import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { assetsInlineLimit: 0, rollupOptions: { output: { manualChunks: { phaser: ['phaser'] } } } },
  server: {
    host: '127.0.0.1',
    strictPort: true,
    proxy: { '/api': process.env.CAMPUS_BACKEND_URL || 'http://127.0.0.1:8000' }
  }
});
