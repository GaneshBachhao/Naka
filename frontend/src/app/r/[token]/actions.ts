"use server";

import { redirect } from "next/navigation";
import { postResponse } from "@/lib/naka-api";

/**
 * Backs the response form's plain HTML <form action={...}>. This is what
 * keeps the page's core interaction working with zero shipped client JS -
 * Next.js progressively enhances a real POST, it doesn't replace it.
 */
export async function recordResponse(formData: FormData): Promise<void> {
  const token = String(formData.get("token") ?? "");
  const kind = String(formData.get("kind") ?? "");

  if (!token) {
    return;
  }

  if (!kind) {
    redirect(`/r/${encodeURIComponent(token)}`);
  }

  const noteRaw = formData.get("note");
  const note = typeof noteRaw === "string" && noteRaw.trim() ? noteRaw.trim() : undefined;

  const priceRaw = formData.get("price_rupees");
  const priceRupees =
    typeof priceRaw === "string" && priceRaw.trim() ? Number(priceRaw) : undefined;
  const price_paise =
    priceRupees !== undefined && Number.isFinite(priceRupees) && priceRupees >= 0
      ? Math.round(priceRupees * 100)
      : undefined;

  const result = await postResponse(token, { kind, note, price_paise });

  if (result.outcome === "recorded") {
    redirect(`/r/${encodeURIComponent(token)}?done=1&first=${result.was_first ? "1" : "0"}`);
  }

  // expired / already_responded / not_found: reload the plain page, which
  // re-fetches fresh state and shows the right card itself.
  redirect(`/r/${encodeURIComponent(token)}`);
}
