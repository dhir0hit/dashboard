import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend lives at http://127.0.0.1:8000 (FastAPI). Dev proxy keeps the
// settings page same-origin so cookies/CORS are not a concern in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/wallpapers": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});