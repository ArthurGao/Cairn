import Link from "next/link";
import type { ReactNode } from "react";

export type Crumb = { label: ReactNode; href?: string };

/** Breadcrumb trail and page title, shared by the case pages. */
export function PageHeader({ crumbs, title, children }: { crumbs: Crumb[]; title: ReactNode; children?: ReactNode }) {
  return (
    <header className="col-span-12 border-b border-ink pb-4">
      <nav aria-label="Breadcrumb" className="text-xs uppercase tracking-wide text-muted">
        {crumbs.map((crumb, n) => (
          <span key={n}>
            {n > 0 && " / "}
            {crumb.href ? (
              <Link href={crumb.href} className="hover:underline">
                {crumb.label}
              </Link>
            ) : (
              crumb.label
            )}
          </span>
        ))}
      </nav>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h1>
      {children}
    </header>
  );
}
