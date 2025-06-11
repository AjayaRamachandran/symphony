// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Optional aliases — uncomment or customize if needed
      '@': path.resolve(__dirname, 'src'),
      // 'components': path.resolve(__dirname, 'src/components'),
      // 'assets': path.resolve(__dirname, 'src/assets'),
    },
  },
});
