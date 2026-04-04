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

  experimental: {
    // Tree-shake heavy packages — only import what's actually used
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

  // Reduce dev memory pressure by limiting concurrent compilations
  ...(isProd ? {} : {
    webpack: (config: any) => {
      config.optimization = {
        ...config.optimization,
        // Reduce parallelism to lower memory usage in dev
        realContentHash: false,
      };
      return config;
    },
  }),
};

export default nextConfig;
