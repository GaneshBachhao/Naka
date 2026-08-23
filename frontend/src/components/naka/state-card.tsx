type StateVariant = "not_found" | "expired" | "already_responded";

const COPY: Record<StateVariant, { title: string; body: string }> = {
  not_found: {
    title: "ही लिंक सापडली नाही",
    body: "कृपया लिंक तपासा. काही अडचण असल्यास पुन्हा विनंतीची वाट पहा.",
  },
  expired: {
    title: "उत्तर देण्याची वेळ संपली",
    body: "या विचारणेला उत्तर देण्याची वेळ संपली आहे. पुढच्या वेळी लवकर उत्तर द्या.",
  },
  already_responded: {
    title: "तुम्ही आधीच उत्तर दिले आहे",
    body: "या विचारणेसाठी तुमचे उत्तर आधीच नोंदवले गेले आहे. धन्यवाद!",
  },
};

/** Expired / already-used / unknown tokens get their own clear state, not
 * an error page - the same screen shape as the question card, just
 * carrying a plain, directive message instead of a form. */
export function StateCard({ variant }: { variant: StateVariant }) {
  const copy = COPY[variant];
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 py-10">
      <div className="flex w-full max-w-md flex-col items-center gap-3 rounded-2xl border-2 border-stone/40 bg-paper px-6 py-12 text-center shadow-md">
        <h1 className="font-heading text-2xl font-extrabold text-ink">{copy.title}</h1>
        <p className="text-lg text-ink">{copy.body}</p>
      </div>
    </main>
  );
}

/** The reward loop: card flips to a large, unmissable confirmation. Plays
 * once on mount via CSS only, and only for viewers who haven't asked for
 * reduced motion. */
export function ConfirmationCard({ wasFirst }: { wasFirst: boolean }) {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 py-10">
      <div className="motion-safe:animate-[naka-flip_0.6s_ease-out] flex w-full max-w-md flex-col items-center gap-4 rounded-2xl bg-field px-6 py-14 text-center text-paper shadow-lg [backface-visibility:hidden]">
        <p className="font-heading text-6xl leading-none font-extrabold">धन्यवाद!</p>
        {wasFirst ? (
          <p className="text-2xl font-bold text-haldi">तुम्ही सर्वात आधी उत्तर दिले!</p>
        ) : (
          <p className="text-xl">तुमचे उत्तर नोंदवले गेले.</p>
        )}
      </div>
    </main>
  );
}
