import { getResponsePage } from "@/lib/naka-api";
import { ResponseForm } from "@/components/naka/response-form";
import { ConfirmationCard, StateCard } from "@/components/naka/state-card";

export default async function DealerResponsePage({
  params,
  searchParams,
}: {
  params: Promise<{ token: string }>;
  searchParams: Promise<{ done?: string; first?: string }>;
}) {
  const { token } = await params;
  const sp = await searchParams;

  if (sp.done === "1") {
    return <ConfirmationCard wasFirst={sp.first === "1"} />;
  }

  const data = await getResponsePage(token);

  if (data.outcome === "not_found") {
    return <StateCard variant="not_found" />;
  }
  if (data.is_expired) {
    return <StateCard variant="expired" />;
  }
  if (data.has_responded) {
    return <StateCard variant="already_responded" />;
  }

  return (
    <ResponseForm
      token={token}
      rawText={data.raw_text ?? ""}
      localityName={data.locality_name}
      minutesAgo={data.minutes_ago ?? 0}
    />
  );
}
