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
