import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output for a lean Docker image (T10) - traces only the
  // files the server actually needs instead of shipping node_modules.
  output: "standalone",
};

export default nextConfig;
