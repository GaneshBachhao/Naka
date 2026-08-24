export function formatAgo(minutesAgo: number): string {
  if (minutesAgo < 1) return "आत्ताच";
  if (minutesAgo < 60) return `${minutesAgo} मिनिटांपूर्वी`;
  const hours = Math.floor(minutesAgo / 60);
  if (hours < 24) return `${hours} तासांपूर्वी`;
  return `${Math.floor(hours / 24)} दिवसांपूर्वी`;
}

/**
 * The customer's question - the visual anchor the three answer buttons
 * sit below.
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
    <div className="rounded-2xl border border-border bg-card px-5 py-6 shadow-sm">
      <p className="text-sm font-semibold tracking-wide text-primary uppercase">नवीन विचारणा</p>
      <p className="mt-2 text-2xl leading-snug font-bold text-balance text-card-foreground">
        {rawText}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-base text-muted-foreground">
        {localityName ? <span>{localityName}</span> : null}
        {localityName ? <span aria-hidden="true">•</span> : null}
        <span>{formatAgo(minutesAgo)}</span>
      </div>
    </div>
  );
}
