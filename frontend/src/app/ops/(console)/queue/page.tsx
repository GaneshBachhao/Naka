// frontend/src/app/ops/(console)/queue/page.tsx
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { listOperatorQueue, markOperatorMessageSent } from "@/lib/ops-api";

export default function OperatorQueuePage() {
  const queryClient = useQueryClient();
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const { data } = useQuery({
    queryKey: ["operator-queue"],
    queryFn: listOperatorQueue,
    refetchInterval: 5_000,
  });

  const markSent = useMutation({
    mutationFn: markOperatorMessageSent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["operator-queue"] }),
  });

  const pending = (data ?? []).filter((m) => m.sent_at === null);

  async function copy(id: string, message: string) {
    await navigator.clipboard.writeText(message);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  }

  return (
    <div className="max-w-2xl">
      <h1 className="mb-3 font-heading text-xl font-bold">Pending outbound messages</h1>
      <p className="mb-4 text-sm text-stone">
        Wizard-of-Oz: copy each message, send it by hand over WhatsApp, then mark it sent.
      </p>
      {pending.length === 0 && <p className="text-stone">Nothing pending.</p>}
      <ul className="flex flex-col gap-3">
        {pending.map((m) => (
          <li key={m.id} className="rounded-md border border-stone/20 p-3 text-sm">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-semibold">
                {m.recipient_kind} · {m.phone_number}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => copy(m.id, m.message)}
                  className="rounded bg-field px-2 py-0.5 text-xs text-paper"
                >
                  {copiedId === m.id ? "Copied!" : "Copy"}
                </button>
                <button
                  onClick={() => markSent.mutate(m.id)}
                  disabled={markSent.isPending}
                  className="rounded bg-haldi px-2 py-0.5 text-xs font-semibold text-ink"
                >
                  Mark sent
                </button>
              </div>
            </div>
            <pre className="whitespace-pre-wrap rounded bg-paper p-2 text-xs">{m.message}</pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
