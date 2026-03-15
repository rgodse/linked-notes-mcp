import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  root: path.resolve(__dirname, "ui"),
  build: {
    outDir: path.resolve(__dirname, "src/linked_notes_mcp/static"),
    emptyOutDir: false,
  },
});
