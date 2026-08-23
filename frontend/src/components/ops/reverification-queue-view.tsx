// frontend/src/components/ops/reverification-queue-view.tsx
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useBusinessNames } from "@/components/ops/use-business-names";
import { getReverificationQueue, recordVerification } from "@/lib/ops-api";

const TIERS = ["field_verified", "owner_confirmed", "contact_verified", "sourced"];
const METHODS = ["field_visit", "owner_confirmation", "phone_call", "public_source"];

export function ReverificationQueueView() {
  const { nameFor } = useBusinessNames();
  const queryClient = useQueryClient();
  const [openFor, setOpenFor] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ["reverification-queue"],
    queryFn: getReverificationQueue,
  });

  const record = useMutation({
    mutationFn: recordVerification,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reverification-queue"] });
      setOpenFor(null);
    },
  });

  return (
    <div className="max-w-2xl">
      <h1 className="mb-3 font-heading text-xl font-bold">Reverification queue</h1>
      <p className="mb-4 text-sm text-stone">
        Ranked: paying businesses first, then routable categories, then oldest verification.
      </p>
      <ul className="flex flex-col gap-2">
        {data?.map((item) => (
          <li key={item.business_id} className="rounded-md border border-stone/20 p-3 text-sm">
            <div className="flex items-center justify-between">
              <span>
                <span className="font-semibold">{nameFor(item.business_id)}</span>
                <span className="text-stone">
                  {" "}
                  · {item.tier} · {item.days_until_decay}d until decay
                  {item.is_paying ? " · paying" : ""}
                  {item.is_routable_category ? " · routable" : ""}
                </span>
              </span>
              <button
                onClick={() => setOpenFor(openFor === item.business_id ? null : item.business_id)}
                className="rounded bg-field px-2 py-0.5 text-xs font-semibold text-paper"
              >
                Record verification
              </button>
            </div>
            {openFor === item.business_id && (
              <VerificationForm
                businessId={item.business_id}
                onSubmit={(body) => record.mutate(body)}
                pending={record.isPending}
              />
            )}
          </li>
        ))}
        {data?.length === 0 && <p className="text-stone">Nothing due.</p>}
      </ul>
    </div>
  );
}

function VerificationForm({
  businessId,
  onSubmit,
  pending,
}: {
  businessId: string;
  onSubmit: (body: {
    business_id: string;
    tier: string;
    method: string;
    verified_by: string;
    notes: string;
  }) => void;
  pending: boolean;
}) {
  const [tier, setTier] = useState(TIERS[0]);
  const [method, setMethod] = useState(METHODS[0]);
  const [verifiedBy, setVerifiedBy] = useState("");
  const [notes, setNotes] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ business_id: businessId, tier, method, verified_by: verifiedBy, notes });
      }}
      className="mt-2 flex flex-wrap items-end gap-2 border-t border-stone/20 pt-2"
    >
      <label className="flex flex-col text-xs text-stone">
        Tier
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="h-8 rounded border border-stone/40 px-1"
        >
          {TIERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col text-xs text-stone">
        Method
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          className="h-8 rounded border border-stone/40 px-1"
        >
          {METHODS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col text-xs text-stone">
        Verified by
        <input
          value={verifiedBy}
          onChange={(e) => setVerifiedBy(e.target.value)}
          required
          className="h-8 rounded border border-stone/40 px-1"
        />
      </label>
      <label className="flex flex-col text-xs text-stone">
        Notes
        <input
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="h-8 rounded border border-stone/40 px-1"
        />
      </label>
      <button
        type="submit"
        disabled={pending}
        className="h-8 rounded bg-field px-3 text-xs font-semibold text-paper disabled:opacity-50"
      >
        Save
      </button>
    </form>
  );
}
