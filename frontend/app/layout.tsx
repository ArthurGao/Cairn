import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import type { ReactNode } from "react";

import { HealthBadge } from "@/components/HealthBadge";

import "./globals.css";
import { Providers } from "./providers";

const sans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex-sans" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });

export const metadata: Metadata = {
  title: "Cairn",
  description: "Case checks for immigration advisers: drafts with sources, adviser signs off.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <Providers>
          <header className="border-b border-ink">
            <div className="mx-auto grid max-w-[1200px] grid-cols-12 items-start gap-6 px-6 py-4">
              <div className="col-span-6 flex items-baseline gap-8">
                <Link href="/cases" className="text-lg font-semibold tracking-tight">
                  Cairn
                </Link>
                <nav aria-label="Main" className="flex gap-6 text-sm">
                  <Link href="/cases" className="hover:underline">
                    Cases
                  </Link>
                </nav>
              </div>
              <div className="col-span-6 flex justify-end">
                <HealthBadge />
              </div>
            </div>
          </header>
          <main className="mx-auto max-w-[1200px] px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
