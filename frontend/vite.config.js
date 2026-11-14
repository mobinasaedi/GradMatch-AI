import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api calls are proxied to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "127.0.0.1",
    proxy: { "/api": process.env.VITE_API_TARGET || "http://127.0.0.1:8000" },
    // Editors that save atomically leave short-lived *.tmpdir folders next to the
    // source file; watching them crashes chokidar on Windows (EBUSY).
    watch: {
      ignored: ["**/*.tmpdir/**", "**/*.tmp", "**/.*.tmpdir/**"],
    },
  },
});
