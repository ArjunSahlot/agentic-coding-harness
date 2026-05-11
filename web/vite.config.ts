import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        configure: (proxy) => {
          proxy.on("error", (_err, _req, res) => {
            if (!res || res.destroyed || res.headersSent) return;
            res.writeHead(503, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ error: "backend_unavailable" }));
          });
        },
      },
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
        configure: (proxy) => {
          proxy.on("error", (_err, _req, socket) => {
            socket?.destroy();
          });
        },
      },
    },
  },
});
