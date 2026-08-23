// frontend/src/lib/ops-api.ts
// Client-side API for the ops console. Unlike naka-api.ts (server-only,
// used from Server Components/Actions), everything here runs in the
// browser: polling for the live queue and response tracking, and keyboard
// shortcuts, both need a client component. There's no login flow yet (T8
// ships before the identity/OTP context), so auth is a bearer token the
// operator pastes once, kept in localStorage and attached by hand here.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "naka-ops-token";

export function getOpsToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setOpsToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearOpsToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class OpsApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getOpsToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new OpsApiError(response.status, detail.detail ?? response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

// --- enquiries ---

export type EnquiryQueueItem = {
  id: string;
  status: string;
  raw_text: string;
  minutes_ago: number;
};

export type ParsedIntent = {
  category_id: string;
  item_text: string;
  locality_id: string;
  urgency: string;
  confidence: number;
  is_advice_request: boolean;
};

export type RoutedRequestDetail = {
  business_id: string;
  sent_at: string;
  expires_at: string;
  responded_at: string | null;
  is_expired: boolean;
};

export type BusinessResponseDetail = {
  business_id: string;
  kind: string;
  price_paise: number | null;
  note: string;
  can_arrange_by: string | null;
  responded_at: string;
};

export type EnquiryDetail = {
  id: string;
  status: string;
  raw_text: string;
  region_id: string;
  created_at: string;
  minutes_ago: number;
  parsed_intent: ParsedIntent | null;
  routed_requests: RoutedRequestDetail[];
  responses: BusinessResponseDetail[];
  winning_business_id: string | null;
};

export type RoutingSuggestion = {
  business_id: string;
  distance_km: number;
  response_rate: number;
  verification_recency_days: number;
  reason: string;
  default_selected: boolean;
};

export type RoutedMessage = {
  business_id: string;
  phone_number: string;
  message: string;
};

export type RouteEnquiryResult = {
  enquiry: { id: string; status: string; routed_business_ids: string[] };
  messages: RoutedMessage[];
};

export type DailyCounters = {
  total_enquiries: number;
  answered: number;
  answer_rate: number;
  median_response_seconds: number | null;
};

export const listEnquiryQueue = () => request<EnquiryQueueItem[]>("/ops/enquiries");

export const getEnquiryDetail = (id: string) => request<EnquiryDetail>(`/ops/enquiries/${id}`);

export const parseEnquiry = (id: string) =>
  request<EnquiryDetail>(`/ops/enquiries/${id}/parse`, { method: "POST" });

export const suggestRoutingCandidates = (id: string) =>
  request<RoutingSuggestion[]>(`/ops/enquiries/${id}/candidates`);

export const routeEnquiry = (id: string, businessIds: string[]) =>
  request<RouteEnquiryResult>(`/ops/enquiries/${id}/route`, {
    method: "POST",
    body: JSON.stringify({ business_ids: businessIds }),
  });

export const getDailyCounters = () => request<DailyCounters>("/ops/counters/daily");

// --- operator queue (Wizard-of-Oz outbound messages) ---

export type OperatorQueueMessage = {
  id: string;
  recipient_kind: string;
  phone_number: string;
  message: string;
  created_at: string;
  sent_at: string | null;
};

export const listOperatorQueue = () => request<OperatorQueueMessage[]>("/ops/operator-queue");

export const markOperatorMessageSent = (id: string) =>
  request<void>(`/ops/operator-queue/${id}/mark-sent`, { method: "POST" });

// --- catalog: businesses, localities, categories ---

export type DayHours = {
  open_time: string | null;
  close_time: string | null;
  midday_break_start: string | null;
  midday_break_end: string | null;
};

export type Business = {
  id: string;
  region_id: string;
  locality_id: string;
  name_mr: string;
  name_en: string;
  owner_name: string;
  category_ids: string[];
  contact_numbers: string[];
  whatsapp_number: string | null;
  landmark: string;
  latitude: number;
  longitude: number;
  opening_hours: Record<number, DayHours>;
  attributes: string[];
  publication_state: string;
};

export type BusinessFormValues = {
  region_id: string;
  locality_id: string;
  name_mr: string;
  name_en: string;
  owner_name: string;
  category_ids: string[];
  contact_numbers: string[];
  whatsapp_number: string | null;
  landmark: string;
  latitude: number;
  longitude: number;
  opening_hours: Record<number, DayHours>;
  attributes: string[];
};

export const listBusinesses = () => request<Business[]>("/ops/businesses");

export const getBusiness = (id: string) => request<Business>(`/ops/businesses/${id}`);

export const createBusiness = (body: BusinessFormValues) =>
  request<Business>("/ops/businesses", { method: "POST", body: JSON.stringify(body) });

export const updateBusiness = (id: string, body: Omit<BusinessFormValues, "region_id">) =>
  request<Business>(`/ops/businesses/${id}`, { method: "PUT", body: JSON.stringify(body) });

export const publishBusiness = (id: string) =>
  request<Business>(`/ops/businesses/${id}/publish`, { method: "POST" });

export type Locality = { id: string; region_id: string; name_mr: string; name_en: string };

export const listLocalities = (regionId: string) =>
  request<Locality[]>(`/ops/localities?region_id=${encodeURIComponent(regionId)}`);

export type Category = {
  id: string;
  slug: string;
  name_mr: string;
  name_en: string;
  tier: number;
  routable: boolean;
};

export const listCategories = () => request<Category[]>("/ops/categories");

// --- verification ---

export type ReverificationQueueItem = {
  business_id: string;
  tier: string;
  days_until_decay: number;
  is_paying: boolean;
  is_routable_category: boolean;
};

export const getReverificationQueue = () =>
  request<ReverificationQueueItem[]>("/ops/reverification-queue");

export type RecordVerificationBody = {
  business_id: string;
  tier: string;
  method: string;
  verified_by: string;
  notes?: string;
};

export const recordVerification = (body: RecordVerificationBody) =>
  request<unknown>("/ops/verifications", { method: "POST", body: JSON.stringify(body) });
