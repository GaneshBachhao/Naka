import { EmergencyNumbersView } from "@/components/naka/emergency-numbers-view";

export default async function Page({ params }: { params: Promise<{ region: string }> }) {
  const { region: slug } = await params;
  return <EmergencyNumbersView regionSlug={slug} />;
}
