import { formatAgo } from "@/components/naka/question-card";
import { PlainCard } from "@/components/naka/plain-card";
import { getEnquiryStatus } from "@/lib/naka-api";

function rupees(pricePaise: number): string {
  return `₹${(pricePaise / 100).toLocaleString("en-IN")}`;
}

export async function EnquiryStatusView({ enquiryId }: { enquiryId: string }) {
  const data = await getEnquiryStatus(enquiryId);

  if (data.outcome === "not_found" || data.status === null) {
    return (
      <PlainCard
        title="ही विचारणा सापडली नाही"
        body="कृपया लिंक तपासा किंवा नवीन प्रश्न विचारा."
      />
    );
  }

  if (data.status === "deflected") {
    return (
      <PlainCard
        title="आम्ही सल्ला देत नाही"
        body="औषध किंवा वैद्यकीय सल्ला आम्ही देत नाही - फक्त कोणाकडे उपलब्ध आहे हे सांगतो. कृपया डॉक्टर किंवा कृषी तज्ञांचा सल्ला घ्या."
      />
    );
  }

  if (data.status === "unanswered") {
    return (
      <PlainCard
        title="कोणीही उत्तर दिले नाही"
        body="माफ करा, कोणत्याही दुकानाने वेळेत उत्तर दिले नाही. कृपया पुन्हा प्रयत्न करा."
      />
    );
  }

  if (data.status === "answered") {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center px-4 py-10">
        <div className="motion-safe:animate-[naka-flip_0.6s_ease-out] flex w-full max-w-md flex-col items-center gap-3 rounded-2xl bg-field px-6 py-14 text-center text-paper shadow-lg [backface-visibility:hidden]">
          <p className="font-heading text-4xl leading-tight font-extrabold">आहे!</p>
          <p className="text-xl">एका दुकानाकडे हे उपलब्ध आहे.</p>
          {data.answer?.price_paise != null && (
            <p className="text-2xl font-bold text-haldi">{rupees(data.answer.price_paise)}</p>
          )}
          {data.answer?.note && <p className="text-lg text-paper/90">{data.answer.note}</p>}
        </div>
      </main>
    );
  }

  // received / parsed / routed - still waiting, keep polling via a plain
  // meta refresh so this stays a real page reload, not client JS.
  const isRouted = data.status === "routed";
  return (
    <>
      <meta httpEquiv="refresh" content="5" />
      <PlainCard
        title={isRouted ? `${data.routed_count ?? 0} दुकानांना विचारले` : "प्रश्न तपासत आहोत"}
        body={
          isRouted
            ? `उत्तराची वाट पाहत आहोत - ${formatAgo(data.minutes_ago ?? 0)} विचारले होते. हे पान आपोआप अद्ययावत होईल.`
            : "काही क्षणात दुकानांना पाठवले जाईल. हे पान आपोआप अद्ययावत होईल."
        }
      />
    </>
  );
}
