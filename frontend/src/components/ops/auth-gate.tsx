// frontend/src/components/ops/auth-gate.tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getOpsToken } from "@/lib/ops-api";

/**
 * Stands in for a login flow that doesn't exist yet (T8 ships before the
 * identity/OTP context). Redirects to the token-entry screen when nothing's
 * stored, so the rest of the console can assume a token is present.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getOpsToken()) {
      router.replace("/ops/login");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) return null;
  return <>{children}</>;
}
