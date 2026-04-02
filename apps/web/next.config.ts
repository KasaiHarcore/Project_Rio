import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  // Only run the React Compiler on components with 'use memo' directive
  // to avoid extra compilation overhead on every component during dev
  reactCompiler: { compilationMode: "annotation" },

  // standalone output is for Docker deployments — skip in dev to avoid trace overhead
  output: isProd ? "standalone" : undefined,

  images: {
    formats: ["image/avif", "image/webp"],
  },

  compress: isProd,

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
