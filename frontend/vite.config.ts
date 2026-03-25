import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api/v1": "http://localhost:3031",
      "/events": "http://localhost:3031",
    },
  },
});
