import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  reactCompiler: { compilationMode: "annotation" },

  output: isProd ? "standalone" : undefined,

  images: {
    formats: ["image/avif", "image/webp"],
  },

  compress: isProd,

  // Disable source maps in production to reduce memory and bundle size
  productionBrowserSourceMaps: false,

  // Turbopack is the default bundler in Next.js 16
  turbopack: {},

  experimental: {
    optimizePackageImports: [
      "framer-motion",
      "lucide-react",
      "@radix-ui/react-tooltip",
      "@radix-ui/react-dialog",
      "three",
      "@react-three/fiber",
      "@react-three/drei",
      "@monaco-editor/react",
      "react-markdown",
      "rehype-katex",
      "remark-gfm",
      "remark-math",
    ],
  },
};

export default nextConfig;
