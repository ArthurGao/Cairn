import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import type { ReactNode } from "react";

import { SiteHeader } from "@/components/SiteHeader";
import { gateFrom } from "@/lib/auth/session";

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
          <SiteHeader signOut={gateFrom(process.env).kind === "on"} />
          <main className="mx-auto max-w-[1200px] px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
