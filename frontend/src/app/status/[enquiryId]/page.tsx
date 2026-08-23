import { EnquiryStatusView } from "@/components/naka/enquiry-status-view";

export default async function Page({ params }: { params: Promise<{ enquiryId: string }> }) {
  const { enquiryId } = await params;
  return <EnquiryStatusView enquiryId={enquiryId} />;
}
