// frontend/src/components/ops/new-business-view.tsx
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { BusinessForm } from "@/components/ops/business-form";
import { createBusiness } from "@/lib/ops-api";

export function NewBusinessView() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const create = useMutation({
    mutationFn: createBusiness,
    onSuccess: (business) => {
      queryClient.invalidateQueries({ queryKey: ["businesses"] });
      router.push(`/ops/businesses/${business.id}`);
    },
  });

  return (
    <div>
      <h1 className="mb-3 font-heading text-xl font-bold">New business</h1>
      <BusinessForm
        onSubmit={(values) => create.mutate(values)}
        pending={create.isPending}
        submitLabel="Create (draft)"
      />
      {create.isError && (
        <p className="mt-2 text-sm text-stop">{(create.error as Error).message}</p>
      )}
    </div>
  );
}
