import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.INTERNAL_API_URL || "http://api:8000"}/api/v1/:path*`,
      },
      {
        source: "/health",
        destination: `${process.env.INTERNAL_API_URL || "http://api:8000"}/health`,
      },
      {
        source: "/ready",
        destination: `${process.env.INTERNAL_API_URL || "http://api:8000"}/ready`,
      },
    ];
  },
};

export default nextConfig;
