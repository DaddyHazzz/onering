import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Suppress source map warnings
  productionBrowserSourceMaps: false,

  // React strict mode
  reactStrictMode: true,
};

export default nextConfig;