import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * 浏览器端构建：避免误解析到 Node 专用入口（如 axios 的 http 适配器、ali-oss 等）。
 * 素材与云存储上传请统一走后端 /api/assets/upload 等接口，勿在前端引入 Node SDK。
 */
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    /** 优先使用 package.json 的 browser 条件，减少 url/stream 等 Node polyfill 警告 */
    conditions: ["browser", "module", "import", "default"],
  },
  optimizeDeps: {
    esbuildOptions: {
      target: "esnext",
    },
  },
});
