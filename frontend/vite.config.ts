import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(__dirname, '../static'),
    emptyOutDir: true,
  },
  server: {
    port: 5175,
    proxy: {
      '/documents': 'http://localhost:8001',
      '/sync': 'http://localhost:8001',
      '/devices': 'http://localhost:8001',
      '/health': 'http://localhost:8001',
    },
  },
});
