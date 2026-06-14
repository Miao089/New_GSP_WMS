import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        qualifications: resolve(__dirname, 'qualifications.html'),
        inbound: resolve(__dirname, 'inbound.html'),
        inventory: resolve(__dirname, 'inventory.html'),
        outbound: resolve(__dirname, 'outbound.html'),
        tms: resolve(__dirname, 'tms.html'),
        audit: resolve(__dirname, 'audit.html'),
      }
    }
  }
});
