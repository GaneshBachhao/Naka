import Link from "next/link";
import { submitEnquiryAction } from "@/app/[region]/actions";

/**
 * The region home's hero - the ask box, not a hero image, per the design
 * brief. A real <form> posting through a Server Action, same near-zero-JS
 * approach as the dealer response page: it works even with JS disabled.
 */
export function AskForm({
  regionId,
  regionSlug,
  regionName,
}: {
  regionId: string;
  regionSlug: string;
  regionName: string;
}) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 px-4 py-10">
      <div className="text-center">
        <p className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
          {regionName}
        </p>
        <h1 className="mt-1 text-3xl leading-tight font-bold text-balance text-foreground">
          कोणाकडे आहे, विचारा
        </h1>
        <p className="mt-2 text-lg text-muted-foreground">
          जवळच्या ३-५ दुकानांना लगेच विचारले जाईल.
        </p>
      </div>

      <form action={submitEnquiryAction} className="flex flex-col gap-4">
        <input type="hidden" name="region_id" value={regionId} />

        <label className="flex flex-col gap-1">
          <span className="text-base font-semibold text-foreground">तुमचा प्रश्न</span>
          <textarea
            name="raw_text"
            required
            rows={3}
            placeholder="उदा. कापसासाठी औषध कोणाकडे आहे?"
            className="rounded-xl border border-input bg-background px-4 py-3 text-lg text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:outline-none"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-base font-semibold text-foreground">तुमचा मोबाईल नंबर</span>
          <input
            type="tel"
            name="customer_phone"
            required
            inputMode="numeric"
            pattern="[0-9]{10}"
            placeholder="9876543210"
            className="h-12 rounded-xl border border-input bg-background px-4 text-lg text-foreground placeholder:text-muted-foreground focus-visible:border-primary focus-visible:outline-none"
          />
        </label>

        <button
          type="submit"
          className="h-14 w-full rounded-xl bg-primary text-xl font-bold text-primary-foreground transition-transform active:translate-y-px"
        >
          विचारा
        </button>
      </form>

      <Link
        href={`/${regionSlug}/emergency`}
        className="text-center text-base font-semibold text-destructive hover:underline"
      >
        आपत्कालीन क्रमांक
      </Link>
    </main>
  );
}
