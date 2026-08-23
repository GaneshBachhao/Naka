// frontend/src/components/ops/edit-business-view.tsx
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { BusinessForm } from "@/components/ops/business-form";
import { getBusiness, publishBusiness, updateBusiness } from "@/lib/ops-api";

export function EditBusinessView() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();

  const businessQuery = useQuery({ queryKey: ["business", id], queryFn: () => getBusiness(id) });

  const update = useMutation({
    mutationFn: (values: Parameters<typeof updateBusiness>[1]) => updateBusiness(id, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["business", id] });
      queryClient.invalidateQueries({ queryKey: ["businesses"] });
    },
  });

  const publish = useMutation({
    mutationFn: () => publishBusiness(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["business", id] });
      queryClient.invalidateQueries({ queryKey: ["businesses"] });
    },
  });

  const business = businessQuery.data;
  if (!business) return <p className="text-stone">Loading...</p>;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h1 className="font-heading text-xl font-bold">{business.name_en}</h1>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-stone">{business.publication_state}</span>
          {(business.publication_state === "draft" || business.publication_state === "suspended") && (
            <button
              onClick={() => publish.mutate()}
              disabled={publish.isPending}
              className="rounded bg-haldi px-2 py-1 text-xs font-semibold text-ink"
            >
              Publish
            </button>
          )}
        </div>
      </div>
      <BusinessForm
        existing={business}
        onSubmit={(values) => update.mutate(values)}
        pending={update.isPending}
        submitLabel="Save changes"
      />
      {update.isSuccess && <p className="mt-2 text-sm text-field">Saved.</p>}
      {update.isError && (
        <p className="mt-2 text-sm text-stop">{(update.error as Error).message}</p>
      )}
    </div>
  );
}
