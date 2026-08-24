// frontend/src/components/ops/console-shell.tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearOpsToken, getDailyCounters } from "@/lib/ops-api";

const NAV = [
  { href: "/ops", label: "Queue" },
  { href: "/ops/businesses", label: "Businesses" },
  { href: "/ops/reverification", label: "Reverification" },
  { href: "/ops/queue", label: "Message queue" },
];

function formatSeconds(seconds: number | null): string {
  if (seconds === null) return "-";
  const minutes = Math.round(seconds / 60);
  return minutes < 1 ? "<1m" : `${minutes}m`;
}

export function ConsoleShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: counters } = useQuery({
    queryKey: ["daily-counters"],
    queryFn: getDailyCounters,
    refetchInterval: 30_000,
  });

  function logout() {
    clearOpsToken();
    router.replace("/ops/login");
  }

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="sticky top-0 z-10 flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-border bg-background px-4 py-2 text-sm">
        <span className="text-lg font-bold">Naka Ops</span>
        <nav className="flex gap-4">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={
                pathname === item.href
                  ? "font-semibold text-primary underline underline-offset-4"
                  : "text-muted-foreground hover:text-foreground"
              }
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-4 text-muted-foreground">
          {counters && (
            <span>
              {counters.total_enquiries} today · {(counters.answer_rate * 100).toFixed(0)}%
              answered · median {formatSeconds(counters.median_response_seconds)}
            </span>
          )}
          <button onClick={logout} className="text-destructive hover:underline">
            Log out
          </button>
        </div>
      </header>
      <main className="p-4">{children}</main>
    </div>
  );
}
