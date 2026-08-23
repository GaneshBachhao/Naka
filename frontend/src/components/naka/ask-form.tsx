import { submitEnquiryAction } from "@/app/[region]/actions";

/**
 * The region home's hero - the ask box, not a hero image, per the design
 * brief. A real <form> posting through a Server Action, same near-zero-JS
 * approach as the dealer response page: it works even with JS disabled.
 */
export function AskForm({ regionId, regionName }: { regionId: string; regionName: string }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 px-4 py-10">
      <div className="text-center">
        <p className="text-sm font-semibold tracking-wide text-stone uppercase">{regionName}</p>
        <h1 className="mt-1 font-heading text-3xl leading-tight font-extrabold text-balance text-ink">
          कोणाकडे आहे, विचारा
        </h1>
        <p className="mt-2 text-lg text-stone">जवळच्या ३-५ दुकानांना लगेच विचारले जाईल.</p>
      </div>

      <form action={submitEnquiryAction} className="flex flex-col gap-4">
        <input type="hidden" name="region_id" value={regionId} />

        <label className="flex flex-col gap-1">
          <span className="text-base font-semibold text-ink">तुमचा प्रश्न</span>
          <textarea
            name="raw_text"
            required
            rows={3}
            placeholder="उदा. कापसासाठी औषध कोणाकडे आहे?"
            className="rounded-xl border-2 border-stone/40 bg-paper px-4 py-3 text-lg text-ink placeholder:text-stone focus-visible:border-field focus-visible:outline-none"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-base font-semibold text-ink">तुमचा मोबाईल नंबर</span>
          <input
            type="tel"
            name="customer_phone"
            required
            inputMode="numeric"
            pattern="[0-9]{10}"
            placeholder="9876543210"
            className="h-14 rounded-xl border-2 border-stone/40 bg-paper px-4 text-lg text-ink placeholder:text-stone focus-visible:border-field focus-visible:outline-none"
          />
        </label>

        <button
          type="submit"
          className="h-16 w-full rounded-xl bg-field text-xl font-bold text-paper transition-transform active:translate-y-px"
        >
          विचारा
        </button>
      </form>
    </main>
  );
}
