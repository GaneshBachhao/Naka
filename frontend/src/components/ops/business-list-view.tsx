// frontend/src/components/ops/business-list-view.tsx
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { listBusinesses, publishBusiness } from "@/lib/ops-api";

const STATE_COLOR: Record<string, string> = {
  draft: "text-stone",
  published_unverified: "text-haldi",
  published_verified: "text-field",
  suspended: "text-stop",
  closed: "text-stop",
};

export function BusinessListView() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["businesses"], queryFn: listBusinesses });

  const publish = useMutation({
    mutationFn: publishBusiness,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["businesses"] }),
  });

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h1 className="font-heading text-xl font-bold">Businesses</h1>
        <Link
          href="/ops/businesses/new"
          className="rounded-md bg-field px-3 py-1.5 text-sm font-semibold text-paper"
        >
          + New business
        </Link>
      </div>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-stone/30 text-left text-stone">
            <th className="py-1 pr-4">Name</th>
            <th className="py-1 pr-4">Owner</th>
            <th className="py-1 pr-4">Status</th>
            <th className="py-1"></th>
          </tr>
        </thead>
        <tbody>
          {data?.map((b) => (
            <tr key={b.id} className="border-b border-stone/10">
              <td className="py-1.5 pr-4">
                <Link href={`/ops/businesses/${b.id}`} className="hover:underline">
                  {b.name_mr} <span className="text-stone">({b.name_en})</span>
                </Link>
              </td>
              <td className="py-1.5 pr-4">{b.owner_name}</td>
              <td className={`py-1.5 pr-4 font-semibold ${STATE_COLOR[b.publication_state] ?? ""}`}>
                {b.publication_state}
              </td>
              <td className="py-1.5">
                {(b.publication_state === "draft" || b.publication_state === "suspended") && (
                  <button
                    onClick={() => publish.mutate(b.id)}
                    disabled={publish.isPending}
                    className="rounded bg-haldi px-2 py-0.5 text-xs font-semibold text-ink"
                  >
                    Publish
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {data?.length === 0 && <p className="mt-2 text-stone">No businesses yet.</p>}
    </div>
  );
}
