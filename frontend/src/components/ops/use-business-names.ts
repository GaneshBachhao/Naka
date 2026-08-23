// frontend/src/components/ops/use-business-names.ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { listBusinesses } from "@/lib/ops-api";

/**
 * Every screen that lists routing candidates, routed requests, or the
 * reverification queue only gets business_id back from the API - verification
 * and enquiry deliberately don't cross into catalog for display names (see
 * enquiry's LocalityLookupPort precedent). Resolving id -> name is a
 * frontend join instead: one cached fetch of the whole (small, single-taluka)
 * business list, shared across every page via react-query's cache.
 */
export function useBusinessNames() {
  const { data } = useQuery({ queryKey: ["businesses"], queryFn: listBusinesses });
  const byId = new Map((data ?? []).map((b) => [b.id, b]));
  return {
    nameFor: (businessId: string) => byId.get(businessId)?.name_mr ?? businessId.slice(0, 8),
    businesses: data ?? [],
  };
}
