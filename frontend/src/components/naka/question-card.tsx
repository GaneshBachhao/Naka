function formatAgo(minutesAgo: number): string {
  if (minutesAgo < 1) return "आत्ताच";
  if (minutesAgo < 60) return `${minutesAgo} मिनिटांपूर्वी`;
  const hours = Math.floor(minutesAgo / 60);
  if (hours < 24) return `${hours} तासांपूर्वी`;
  return `${Math.floor(hours / 24)} दिवसांपूर्वी`;
}

/**
 * The customer's question, styled like a chalk price board outside an agri
 * shop - the visual anchor the three answer buttons sit below.
 */
export function QuestionCard({
  rawText,
  localityName,
  minutesAgo,
}: {
  rawText: string;
  localityName: string | null;
  minutesAgo: number;
}) {
  return (
    <div className="rounded-2xl border-4 border-haldi/70 bg-ink px-5 py-6 text-paper shadow-lg">
      <p className="text-sm font-semibold tracking-wide text-haldi uppercase">नवीन विचारणा</p>
      <p className="mt-2 font-heading text-2xl leading-snug font-extrabold text-balance">
        {rawText}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-base text-paper/85">
        {localityName ? <span>{localityName}</span> : null}
        {localityName ? <span aria-hidden="true">•</span> : null}
        <span>{formatAgo(minutesAgo)}</span>
      </div>
    </div>
  );
}
