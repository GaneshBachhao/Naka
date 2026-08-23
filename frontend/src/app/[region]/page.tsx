import { AskForm } from "@/components/naka/ask-form";
import { PlainCard } from "@/components/naka/plain-card";
import { getRegion } from "@/lib/naka-api";

export default async function RegionHomePage({
  params,
}: {
  params: Promise<{ region: string }>;
}) {
  const { region: slug } = await params;
  const region = await getRegion(slug);

  if (region === null) {
    return (
      <PlainCard
        title="हा भाग सापडला नाही"
        body="कृपया लिंक तपासा किंवा योग्य भागाची लिंक वापरा."
      />
    );
  }

  return <AskForm regionId={region.id} regionSlug={region.slug} regionName={region.name_mr} />;
}
