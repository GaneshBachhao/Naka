// frontend/src/components/ops/token-login-view.tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { setOpsToken } from "@/lib/ops-api";

export function TokenLoginView() {
  const router = useRouter();
  const [token, setToken] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token.trim()) return;
    setOpsToken(token.trim());
    router.replace("/ops");
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-4 px-4">
      <h1 className="text-2xl font-bold text-foreground">Naka Ops</h1>
      <p className="text-sm text-muted-foreground">
        Paste the operator token minted with <code>make ops-token</code>. There&apos;s no login
        flow yet - this is a stand-in until the identity context ships.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          autoFocus
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="eyJhbGci..."
          className="h-11 rounded-md border border-input bg-background px-3 font-mono text-sm text-foreground focus-visible:border-primary focus-visible:outline-none"
        />
        <button
          type="submit"
          className="h-11 rounded-md bg-primary text-sm font-semibold text-primary-foreground"
        >
          Enter console
        </button>
      </form>
    </main>
  );
}
