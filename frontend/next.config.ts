import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A self-contained server for the demo image (deploy/oracle); `next dev` is unaffected.
  output: "standalone",
};

export default nextConfig;
