import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendPort = process.env.BACKEND_PORT || "8002";
const backendTarget = `http://127.0.0.1:${backendPort}`;
const frontendPort = parseInt(process.env.PORT || "5175", 10);

export default defineConfig({
  plugins: [react()],
  server: {
    port: frontendPort,
    proxy: {
      "/session": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/health": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/menu": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/cart": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/order": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/message": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/tts": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/stt": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/screen": {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
  },
});
