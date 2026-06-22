import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Static SPA. Relative base so the build works from any path / file://.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    fs: { allow: [".."] },
  },
});
