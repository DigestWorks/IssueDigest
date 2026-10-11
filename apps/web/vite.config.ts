import { reactRouter } from '@react-router/dev/vite';
import { defineConfig } from 'vite';

// Server-side development setting only; never exposed through a VITE_* variable.
const target = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000';
export default defineConfig({
  plugins: [reactRouter()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target }, '/health': { target } },
  },
});
