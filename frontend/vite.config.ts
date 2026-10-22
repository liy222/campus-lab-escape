import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { outDir: process.env.VITE_GAMEPLAY_VERSION === 'v5' ? 'dist-v5' : 'dist', assetsInlineLimit: 0, rollupOptions: { output: { manualChunks: { phaser: ['phaser'] } } } },
  server: {
    host: '127.0.0.1',
    strictPort: true,
    proxy: { '/api': process.env.VITE_GAMEPLAY_VERSION === 'v5' ? { target: process.env.CAMPUS_BACKEND_URL || 'http://127.0.0.1:8001', changeOrigin: true, xfwd: false } : process.env.CAMPUS_BACKEND_URL || 'http://127.0.0.1:8000' }
  }
});
