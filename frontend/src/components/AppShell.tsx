"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { ArrowLeft, CloudSun, Home, ScanSearch, ShieldCheck, type LucideIcon } from "lucide-react";
import { cn } from "./ui";

const NAV_ITEMS: { href: string; label: string; icon: LucideIcon }[] = [
  { href: "/dashboard", label: "Beranda", icon: Home },
  { href: "/diagnosis", label: "Periksa", icon: ScanSearch },
  { href: "/weather", label: "Cuaca", icon: CloudSun },
  { href: "/insurance", label: "Asuransi", icon: ShieldCheck },
];

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Menu utama"
      className="fixed inset-x-0 bottom-0 z-30 mx-auto w-full max-w-[480px] border-t border-border bg-card/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-sm"
    >
      <ul className="grid grid-cols-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-16 flex-col items-center justify-center gap-1 text-[13px] font-semibold transition-colors duration-150",
                  "focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring",
                  active ? "text-primary" : "text-muted-foreground active:bg-muted"
                )}
              >
                <span
                  className={cn(
                    "inline-flex h-8 w-14 items-center justify-center rounded-full transition-colors duration-150",
                    active && "bg-success-border/60"
                  )}
                >
                  <Icon className="size-6" strokeWidth={active ? 2.4 : 2} aria-hidden="true" />
                </span>
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function AppHeader({
  title,
  backHref,
  action,
}: {
  title: string;
  backHref?: string;
  action?: ReactNode;
}) {
  const router = useRouter();
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-card/95 pt-[env(safe-area-inset-top)] backdrop-blur-sm">
      <div className="flex min-h-16 items-center gap-1 px-2">
        {backHref ? (
          <button
            type="button"
            onClick={() => (window.history.length > 1 ? router.back() : router.push(backHref))}
            aria-label="Kembali"
            className="inline-flex size-12 cursor-pointer items-center justify-center rounded-full text-foreground active:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
          >
            <ArrowLeft className="size-6" aria-hidden="true" />
          </button>
        ) : (
          <span className="w-3" />
        )}
        <h1 className="flex-1 truncate text-lg font-bold text-foreground">{title}</h1>
        {action}
      </div>
    </header>
  );
}

/** Page wrapper: reserves space for the bottom nav so content is never hidden behind it. */
export function PageShell({
  children,
  withNav = true,
  busy = false,
}: {
  children: ReactNode;
  withNav?: boolean;
  busy?: boolean;
}) {
  return (
    <>
      <main
        aria-busy={busy || undefined}
        className={cn("min-h-dvh", withNav ? "pb-[calc(5.5rem+env(safe-area-inset-bottom))]" : "pb-8")}
      >
        {children}
      </main>
      {withNav && <BottomNav />}
    </>
  );
}
