import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "og-image.png"],
      manifest: {
        name: "LangWeave 情感陪伴",
        short_name: "LangWeave",
        description:
          "LangWeave 情感陪伴助手提供温暖、共情的 AI 对话支持。",
        theme_color: "#d9735a",
        background_color: "#f5f2ef",
        display: "standalone",
        orientation: "portrait",
        lang: "zh-CN",
        categories: ["health", "lifestyle", "communication"],
        icons: [
          {
            src: "/icon-192x192.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any maskable",
          },
          {
            src: "/icon-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,jpg,gif,ico}"],
        runtimeCaching: [
          {
            urlPattern: /^https?:\/\/chat\.mybfs\.cn\/api\/.*/i,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
              networkTimeoutSeconds: 10,
            },
          },
        ],
      },
    }),
  ],
  build: {
    rollupOptions: {
      input: "app.html",
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
