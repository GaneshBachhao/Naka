import { PlainCard } from "@/components/naka/plain-card";
import { getRegion } from "@/lib/naka-api";

// Only India-wide numbers here - real, verified, safe to publish. Hyperlocal
// contacts (police station, primary health center) need real verified data
// before they can be shown; a wrong emergency number is actively dangerous,
// so a placeholder beats a guess.
const NATIONAL_NUMBERS = [
  { label: "सर्व आपत्कालीन सेवा (एकत्रित)", number: "112" },
  { label: "पोलीस", number: "100" },
  { label: "अग्निशमन दल", number: "101" },
  { label: "रुग्णवाहिका", number: "102" },
];

export async function EmergencyNumbersView({ regionSlug }: { regionSlug: string }) {
  const region = await getRegion(regionSlug);

  if (region === null) {
    return (
      <PlainCard
        title="हा भाग सापडला नाही"
        body="कृपया लिंक तपासा किंवा योग्य भागाची लिंक वापरा."
      />
    );
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 px-4 py-10">
      <div className="text-center">
        <p className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
          {region.name_mr}
        </p>
        <h1 className="mt-1 text-2xl font-bold text-foreground">आपत्कालीन क्रमांक</h1>
      </div>

      <ul className="flex flex-col gap-3">
        {NATIONAL_NUMBERS.map((entry) => (
          <li key={entry.number}>
            <a
              href={`tel:${entry.number}`}
              className="flex h-14 items-center justify-between rounded-xl border border-destructive/40 bg-card px-5 text-lg font-semibold text-foreground"
            >
              {entry.label}
              <span className="text-2xl font-bold text-destructive">{entry.number}</span>
            </a>
          </li>
        ))}
      </ul>

      <p className="rounded-xl border border-border bg-card px-4 py-3 text-center text-base text-muted-foreground">
        {region.name_mr} मधील स्थानिक पोलीस स्टेशन आणि दवाखान्याचे क्रमांक लवकरच जोडले जातील.
      </p>
    </main>
  );
}
