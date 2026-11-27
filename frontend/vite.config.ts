import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In development the Django API runs on :8000; in production Django serves this build itself.
    proxy: { "/api": process.env.API_PROXY ?? "http://localhost:8000" },
  },
  build: {
    outDir: "dist",
    chunkSizeWarningLimit: 700,
  },
  test: { environment: "node" },
});
