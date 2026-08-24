/** Shared shape for any full-screen "plain, directive" state message -
 * unknown region, expired token, nobody answered, and so on. Never an
 * apologetic error page, per the design brief. */
export function PlainCard({ title, body }: { title: string; body: string }) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 py-10">
      <div className="flex w-full max-w-md flex-col items-center gap-3 rounded-2xl border border-border bg-card px-6 py-12 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-card-foreground">{title}</h1>
        <p className="text-lg text-muted-foreground">{body}</p>
      </div>
    </main>
  );
}
