import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typescript: {
    // Database bindings are provided by the Cloudflare runtime, not Vercel.
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
