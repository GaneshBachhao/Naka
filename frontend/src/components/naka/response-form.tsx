import { recordResponse } from "@/app/r/[token]/actions";
import { QuestionCard } from "@/components/naka/question-card";

type Tone = "have" | "dont" | "later";

const TONE_CHECKED_CLASS: Record<Tone, string> = {
  have: "has-checked:border-field has-checked:bg-field has-checked:text-paper",
  dont: "has-checked:border-stop has-checked:bg-stop has-checked:text-paper",
  later: "has-checked:border-haldi has-checked:bg-haldi has-checked:text-ink",
};

/**
 * The dealer response page - the single most important screen in the
 * product. Server-rendered, zero client JS: the three answers are radio
 * inputs styled as full-width buttons, the optional price/note fields for
 * "have it" reveal via a pure CSS :has() selector, and the whole thing
 * submits through a real HTML form wired to a Server Action - it works
 * even with JS disabled.
 */
export function ResponseForm({
  token,
  rawText,
  localityName,
  minutesAgo,
}: {
  token: string;
  rawText: string;
  localityName: string | null;
  minutesAgo: number;
}) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 px-4 py-10">
      <QuestionCard rawText={rawText} localityName={localityName} minutesAgo={minutesAgo} />

      <form action={recordResponse} className="flex flex-col gap-4">
        <input type="hidden" name="token" value={token} />

        {/*
         * has-[#have_it:checked] lives on the fieldset (an ancestor of
         * both #have_it and .price-fields) because :has() only matches
         * an element's own descendants - #have_it and .price-fields are
         * siblings of each other, not descendants of one another, so the
         * condition has to be evaluated one level up and applied back
         * down via a descendant selector.
         */}
        <fieldset className="flex flex-col gap-3 has-[#have_it:checked]:[&_.price-fields]:flex">
          <legend className="mb-1 text-lg font-semibold text-ink">तुमचे उत्तर निवडा</legend>

          <AnswerOption
            id="have_it"
            value="have_it"
            label="आहे"
            hint="उपलब्ध आहे"
            tone="have"
            icon={<CheckIcon />}
          />
          <AnswerOption
            id="dont_have"
            value="dont_have"
            label="नाही"
            hint="उपलब्ध नाही"
            tone="dont"
            icon={<CrossIcon />}
          />
          <AnswerOption
            id="can_arrange"
            value="can_arrange_by"
            label="नंतर मिळेल"
            hint="काही दिवसांत मिळेल"
            tone="later"
            icon={<ClockIcon />}
          />

          {/* Revealed only when "आहे" is checked - pure CSS, no JS. */}
          <div className="price-fields hidden flex-col gap-3 rounded-xl border-2 border-stone/30 bg-paper p-4">
            <label className="flex flex-col gap-1">
              <span className="text-base font-semibold text-ink">किंमत (ऐच्छिक)</span>
              <input
                type="number"
                name="price_rupees"
                inputMode="decimal"
                min={0}
                step="1"
                placeholder="₹"
                className="h-14 rounded-lg border-2 border-stone/40 bg-paper px-4 text-lg text-ink placeholder:text-stone focus-visible:border-field focus-visible:outline-none"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-base font-semibold text-ink">टीप (ऐच्छिक)</span>
              <input
                type="text"
                name="note"
                maxLength={140}
                className="h-14 rounded-lg border-2 border-stone/40 bg-paper px-4 text-lg text-ink focus-visible:border-field focus-visible:outline-none"
              />
            </label>
          </div>
        </fieldset>

        <button
          type="submit"
          className="h-16 w-full rounded-xl bg-field text-xl font-bold text-paper transition-transform active:translate-y-px"
        >
          पाठवा
        </button>
      </form>
    </main>
  );
}

function AnswerOption({
  id,
  value,
  label,
  hint,
  tone,
  icon,
}: {
  id: string;
  value: string;
  label: string;
  hint: string;
  tone: Tone;
  icon: React.ReactNode;
}) {
  return (
    <label
      htmlFor={id}
      className={`flex min-h-14 w-full cursor-pointer items-center gap-4 rounded-xl border-2 border-stone/40 bg-paper px-5 py-4 text-ink transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-field ${TONE_CHECKED_CLASS[tone]}`}
    >
      <input type="radio" name="kind" id={id} value={value} required className="sr-only" />
      <span aria-hidden="true" className="shrink-0">
        {icon}
      </span>
      <span className="flex flex-col">
        <span className="text-xl font-bold">{label}</span>
        <span className="text-sm font-medium opacity-80">{hint}</span>
      </span>
    </label>
  );
}

function CheckIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
      <path d="M4 12.5 9.5 18 20 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CrossIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
      <path d="M5 5l14 14M19 5 5 19" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
