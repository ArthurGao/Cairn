import type { Metadata } from "next";
import type { ReactNode } from "react";

import { HealthBadge } from "@/components/HealthBadge";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Cairn",
  description: "Case checks for immigration advisers: drafts with sources, adviser signs off.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <header className="flex items-start justify-between border-b border-neutral-300 px-6 py-4">
            <span className="text-lg font-semibold">Cairn</span>
            <HealthBadge />
          </header>
          <main className="px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
