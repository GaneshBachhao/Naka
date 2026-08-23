// frontend/src/components/ops/enquiry-detail-view.tsx
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useBusinessNames } from "@/components/ops/use-business-names";
import {
  type RoutedMessage,
  getEnquiryDetail,
  parseEnquiry,
  routeEnquiry,
  suggestRoutingCandidates,
} from "@/lib/ops-api";

function responseLabel(kind: string): string {
  return { have_it: "आहे", dont_have: "नाही", can_arrange_by: "नंतर मिळेल" }[kind] ?? kind;
}

export function EnquiryDetailView() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const queryClient = useQueryClient();
  const { nameFor } = useBusinessNames();
  const [selectedIds, setSelectedIds] = useState<Set<string> | null>(null);
  const [lastRouteMessages, setLastRouteMessages] = useState<RoutedMessage[] | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const detailQuery = useQuery({
    queryKey: ["enquiry", id],
    queryFn: () => getEnquiryDetail(id),
    refetchInterval: 4_000,
  });
  const enquiry = detailQuery.data;
  const isParsedNotRouted =
    enquiry?.status === "parsed" && enquiry.routed_requests.length === 0;

  const candidatesQuery = useQuery({
    queryKey: ["candidates", id],
    queryFn: () => suggestRoutingCandidates(id),
    enabled: Boolean(isParsedNotRouted),
  });

  useEffect(() => {
    if (candidatesQuery.data && selectedIds === null) {
      setSelectedIds(
        new Set(candidatesQuery.data.filter((c) => c.default_selected).map((c) => c.business_id)),
      );
    }
  }, [candidatesQuery.data, selectedIds]);

  const parseMutation = useMutation({
    mutationFn: () => parseEnquiry(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["enquiry", id] }),
  });

  const routeMutation = useMutation({
    mutationFn: (businessIds: string[]) => routeEnquiry(id, businessIds),
    onSuccess: (result) => {
      setLastRouteMessages(result.messages);
      queryClient.invalidateQueries({ queryKey: ["enquiry", id] });
    },
  });

  function toggle(businessId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev ?? []);
      if (next.has(businessId)) next.delete(businessId);
      else next.add(businessId);
      return next;
    });
  }

  async function copy(message: RoutedMessage) {
    await navigator.clipboard.writeText(message.message);
    setCopiedId(message.business_id);
    setTimeout(() => setCopiedId(null), 1500);
  }

  if (detailQuery.isLoading) return <p className="text-stone">Loading...</p>;
  if (!enquiry) return <p className="text-stop">Enquiry not found.</p>;

  const selectedCount = selectedIds?.size ?? 0;

  return (
    <div className="max-w-2xl">
      <button onClick={() => router.push("/ops")} className="mb-3 text-sm text-stone hover:underline">
        ← back to queue
      </button>

      <h1 className="mb-1 font-heading text-xl font-bold">{enquiry.raw_text}</h1>
      <p className="mb-4 text-sm text-stone">
        {enquiry.minutes_ago}m ago · status:{" "}
        <span className="font-semibold text-ink">{enquiry.status}</span>
      </p>

      {enquiry.status === "deflected" && (
        <p className="rounded-md bg-stop/10 p-3 text-sm text-stop">
          Deflected - this looks like an advice request (pesticide/medical), not an availability
          question. Never routed, per policy.
        </p>
      )}

      {enquiry.status === "received" && (
        <button
          onClick={() => parseMutation.mutate()}
          disabled={parseMutation.isPending}
          className="h-10 rounded-md bg-field px-4 text-sm font-semibold text-paper disabled:opacity-50"
        >
          {parseMutation.isPending ? "Parsing..." : "Parse intent"}
        </button>
      )}

      {enquiry.parsed_intent && (
        <div className="mb-4 rounded-md border border-stone/20 p-3 text-sm">
          <p>
            <span className="text-stone">item: </span>
            {enquiry.parsed_intent.item_text}
          </p>
          <p>
            <span className="text-stone">urgency: </span>
            {enquiry.parsed_intent.urgency}
            <span className="text-stone"> · confidence: </span>
            {(enquiry.parsed_intent.confidence * 100).toFixed(0)}%
          </p>
        </div>
      )}

      {isParsedNotRouted && (
        <div>
          <h2 className="mb-2 font-semibold">
            Suggested businesses{" "}
            <span className="text-sm font-normal text-stone">
              ({selectedCount} selected - edit before routing)
            </span>
          </h2>
          {candidatesQuery.isLoading && <p className="text-stone">Loading candidates...</p>}
          {candidatesQuery.data?.length === 0 && (
            <p className="text-stop">No eligible businesses for this category/locality.</p>
          )}
          <ul className="mb-3 flex flex-col gap-1">
            {candidatesQuery.data?.map((c) => (
              <li key={c.business_id} className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selectedIds?.has(c.business_id) ?? false}
                  onChange={() => toggle(c.business_id)}
                  className="mt-1"
                />
                <span>
                  <span className="font-semibold">{nameFor(c.business_id)}</span>
                  <span className="text-stone"> - {c.reason}</span>
                </span>
              </li>
            ))}
          </ul>
          <button
            onClick={() => routeMutation.mutate(Array.from(selectedIds ?? []))}
            disabled={
              routeMutation.isPending || selectedCount < 3 || selectedCount > 5
            }
            className="h-10 rounded-md bg-field px-4 text-sm font-semibold text-paper disabled:opacity-50"
          >
            {routeMutation.isPending ? "Routing..." : `Route to ${selectedCount} businesses`}
          </button>
          {(selectedCount < 3 || selectedCount > 5) && (
            <p className="mt-1 text-xs text-stop">Fan-out must be between 3 and 5 businesses.</p>
          )}
          {routeMutation.isError && (
            <p className="mt-1 text-xs text-stop">{(routeMutation.error as Error).message}</p>
          )}
        </div>
      )}

      {lastRouteMessages && (
        <div className="mb-4 rounded-md border border-haldi/40 bg-haldi/10 p-3">
          <h2 className="mb-2 font-semibold">Send these by hand (Wizard-of-Oz)</h2>
          <ul className="flex flex-col gap-2">
            {lastRouteMessages.map((m) => (
              <li key={m.business_id} className="text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">
                    {nameFor(m.business_id)} · {m.phone_number}
                  </span>
                  <button
                    onClick={() => copy(m)}
                    className="rounded bg-field px-2 py-0.5 text-xs text-paper"
                  >
                    {copiedId === m.business_id ? "Copied!" : "Copy"}
                  </button>
                </div>
                <pre className="whitespace-pre-wrap rounded bg-paper p-2 text-xs">{m.message}</pre>
              </li>
            ))}
          </ul>
        </div>
      )}

      {enquiry.routed_requests.length > 0 && (
        <div>
          <h2 className="mb-2 font-semibold">Responses</h2>
          <ul className="flex flex-col gap-1 text-sm">
            {enquiry.routed_requests.map((rr) => {
              const response = enquiry.responses.find((r) => r.business_id === rr.business_id);
              const isWinner = enquiry.winning_business_id === rr.business_id;
              return (
                <li
                  key={rr.business_id}
                  className={`flex items-center justify-between rounded px-2 py-1 ${
                    isWinner ? "bg-field/10" : ""
                  }`}
                >
                  <span className={isWinner ? "font-semibold text-field" : ""}>
                    {nameFor(rr.business_id)}
                    {isWinner ? " (first to answer)" : ""}
                  </span>
                  <span className="text-stone">
                    {response
                      ? responseLabel(response.kind)
                      : rr.is_expired
                        ? "expired, no answer"
                        : "waiting..."}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
