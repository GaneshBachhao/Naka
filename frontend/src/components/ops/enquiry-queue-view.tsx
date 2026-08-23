// frontend/src/components/ops/enquiry-queue-view.tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { listEnquiryQueue } from "@/lib/ops-api";

const STATUS_COLOR: Record<string, string> = {
  received: "text-stone",
  parsed: "text-stone",
  routed: "text-haldi",
  answered: "text-field",
  unanswered: "text-stop",
  deflected: "text-stop",
  closed: "text-stone",
};

export function EnquiryQueueView() {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["enquiry-queue"],
    queryFn: listEnquiryQueue,
    refetchInterval: 5_000,
  });
  const [selected, setSelected] = useState(0);

  const items = useMemo(() => data ?? [], [data]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (items.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelected((i) => Math.min(i + 1, items.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelected((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        router.push(`/ops/enquiries/${items[selected].id}`);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [items, selected, router]);

  return (
    <div>
      <h1 className="mb-3 font-heading text-xl font-bold">
        Live enquiry queue{" "}
        <span className="text-sm font-normal text-stone">(↑↓ to move, Enter to open)</span>
      </h1>
      {isLoading && <p className="text-stone">Loading...</p>}
      {!isLoading && items.length === 0 && <p className="text-stone">No enquiries yet.</p>}
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-stone/30 text-left text-stone">
            <th className="py-1 pr-4">Age</th>
            <th className="py-1 pr-4">Status</th>
            <th className="py-1">Text</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr
              key={item.id}
              onClick={() => router.push(`/ops/enquiries/${item.id}`)}
              className={`cursor-pointer border-b border-stone/10 ${
                i === selected ? "bg-field/10" : "hover:bg-stone/5"
              }`}
            >
              <td className="py-1.5 pr-4 tabular-nums text-stone">{item.minutes_ago}m</td>
              <td className={`py-1.5 pr-4 font-semibold ${STATUS_COLOR[item.status] ?? ""}`}>
                {item.status}
              </td>
              <td className="max-w-xl truncate py-1.5">{item.raw_text}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
