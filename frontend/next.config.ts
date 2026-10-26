import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A self-contained server for the demo image (deploy/oracle); `next dev` is unaffected.
  output: "standalone",
  // The sign-in e2e runs its own dev server next to the usual one (playwright.gate.config.ts).
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
