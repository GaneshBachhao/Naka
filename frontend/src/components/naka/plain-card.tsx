/** Shared shape for any full-screen "plain, directive" state message -
 * unknown region, expired token, nobody answered, and so on. Never an
 * apologetic error page, per the design brief. */
export function PlainCard({ title, body }: { title: string; body: string }) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 py-10">
      <div className="flex w-full max-w-md flex-col items-center gap-3 rounded-2xl border-2 border-stone/40 bg-paper px-6 py-12 text-center shadow-md">
        <h1 className="font-heading text-2xl font-extrabold text-ink">{title}</h1>
        <p className="text-lg text-ink">{body}</p>
      </div>
    </main>
  );
}
