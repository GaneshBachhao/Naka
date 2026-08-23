const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export type ResponsePageData = {
  outcome: "found" | "not_found";
  raw_text: string | null;
  locality_id: string | null;
  locality_name: string | null;
  minutes_ago: number | null;
  is_expired: boolean | null;
  has_responded: boolean | null;
};

/**
 * GET /r/{token} - always fetched fresh. Token state (expired, used) is
 * exactly the kind of thing that must never be served stale.
 */
export async function getResponsePage(token: string): Promise<ResponsePageData> {
  const response = await fetch(`${API_BASE_URL}/r/${encodeURIComponent(token)}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return {
      outcome: "not_found",
      raw_text: null,
      locality_id: null,
      locality_name: null,
      minutes_ago: null,
      is_expired: null,
      has_responded: null,
    };
  }
  return response.json();
}

export type RecordResponseOutcome = "recorded" | "not_found" | "expired" | "already_responded";

export type RecordResponseResult = {
  outcome: RecordResponseOutcome;
  was_first: boolean;
};

export async function postResponse(
  token: string,
  body: { kind: string; price_paise?: number; note?: string },
): Promise<RecordResponseResult> {
  const response = await fetch(`${API_BASE_URL}/r/${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    return { outcome: "not_found", was_first: false };
  }
  return response.json();
}

export type Region = {
  id: string;
  slug: string;
  name_mr: string;
  name_hi: string;
  name_en: string;
  district: string;
  state: string;
};

/** GET /api/regions/{slug} - backs /[region]. Not found (unknown or
 * inactive slug) is a normal outcome, not an error - the route itself
 * decides what to render, same as getResponsePage's not_found handling. */
export async function getRegion(slug: string): Promise<Region | null> {
  const response = await fetch(`${API_BASE_URL}/api/regions/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });
  if (!response.ok) return null;
  return response.json();
}

export type SubmitEnquiryResult = { id: string; status: string };

export async function submitEnquiry(body: {
  region_id: string;
  raw_text: string;
  customer_phone: string;
}): Promise<SubmitEnquiryResult> {
  const response = await fetch(`${API_BASE_URL}/api/enquiries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail.detail ?? "enquiry submission failed");
  }
  return response.json();
}

export type WinningAnswer = { price_paise: number | null; note: string };

export type EnquiryStatus = {
  outcome: "found" | "not_found";
  status: string | null;
  minutes_ago: number | null;
  routed_count: number | null;
  answer: WinningAnswer | null;
};

/**
 * GET /api/enquiries/{id}/status - backs the ask box's live wait page.
 * Always fetched fresh, since "still waiting" vs "answered" is exactly
 * the kind of state that must never be served stale.
 */
export async function getEnquiryStatus(enquiryId: string): Promise<EnquiryStatus> {
  const response = await fetch(`${API_BASE_URL}/api/enquiries/${enquiryId}/status`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return { outcome: "not_found", status: null, minutes_ago: null, routed_count: null, answer: null };
  }
  return response.json();
}
