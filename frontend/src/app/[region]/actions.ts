"use server";

import { redirect } from "next/navigation";
import { submitEnquiry } from "@/lib/naka-api";

/**
 * Backs the ask box's plain HTML <form action={...}> - a real POST, not a
 * client-side fetch, so the core interaction works even with JS disabled
 * (same approach as T7's dealer response form).
 */
export async function submitEnquiryAction(formData: FormData): Promise<void> {
  const regionId = String(formData.get("region_id") ?? "");
  const rawText = String(formData.get("raw_text") ?? "").trim();
  const customerPhone = String(formData.get("customer_phone") ?? "").trim();

  if (!regionId || !rawText || !customerPhone) {
    return;
  }

  const enquiry = await submitEnquiry({
    region_id: regionId,
    raw_text: rawText,
    customer_phone: customerPhone,
  });

  redirect(`/status/${enquiry.id}`);
}
