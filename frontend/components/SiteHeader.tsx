"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { HealthBadge } from "@/components/HealthBadge";
import { LOGIN_PATH, forgetCredential } from "@/lib/auth/credential";

const MANAGE = [
  ["/manage/runs", "Runs"],
  ["/manage/context", "Context"],
  ["/manage/memory", "Memory"],
  ["/manage/skills", "Skills"],
  ["/manage/cleanup", "Cleanup"],
];

function SignOutButton() {
  const router = useRouter();
  async function signOut() {
    forgetCredential();
    await fetch("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace(LOGIN_PATH);
  }
  return (
    <button type="button" onClick={signOut} className="border border-rule px-3 py-1 text-sm">
      Sign out
    </button>
  );
}

/** Site header; on /login only the name (no navigation, no API calls before signing in). */
export function SiteHeader({ signOut }: { signOut: boolean }) {
  const onLogin = usePathname() === LOGIN_PATH;
  return (
    <header className="border-b border-ink">
      <div className="mx-auto grid max-w-[1200px] grid-cols-12 items-start gap-6 px-6 py-4">
        <div className="col-span-6 flex items-baseline gap-8">
          <Link href="/cases" className="text-lg font-semibold tracking-tight">
            Cairn
          </Link>
          {!onLogin && (
            <nav aria-label="Main" className="flex gap-6 text-sm">
              <Link href="/cases" className="hover:underline">
                Cases
              </Link>
              <span className="text-muted" aria-hidden>
                |
              </span>
              <span className="sr-only">Manage:</span>
              {MANAGE.map(([href, label]) => (
                <Link key={href} href={href} className="text-muted hover:text-ink hover:underline">
                  {label}
                </Link>
              ))}
            </nav>
          )}
        </div>
        {!onLogin && (
          <div className="col-span-6 flex items-start justify-end gap-4">
            <HealthBadge />
            {signOut && <SignOutButton />}
          </div>
        )}
      </div>
    </header>
  );
}
