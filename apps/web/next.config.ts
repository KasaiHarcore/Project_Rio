import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  output: "standalone",

  images: {
    formats: ["image/avif", "image/webp"],
  },

  // Minify and compress output
  compress: true,

  // Reduce unused JS shipped to client
  modularizeImports: {
    "lucide-react": {
      transform: "lucide-react/dist/esm/icons/{{kebabCase member}}",
    },
  },

  experimental: {
    optimizePackageImports: [
      "framer-motion",
      "lucide-react",
      "@radix-ui/react-tooltip",
      "@radix-ui/react-dialog",
    ],
  },
};

export default nextConfig;
