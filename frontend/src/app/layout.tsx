import type { Metadata } from "next";
import { Anek_Devanagari, Mukta } from "next/font/google";
import "./globals.css";

// Mukta: Devanagari and Latin drawn as one harmonised family (Ek Type), so
// Marathi and English sit correctly on the same line. Never fall back to a
// Latin-first font for Devanagari - the vertical metrics break and it
// looks cheap, per the design brief.
const mukta = Mukta({
  variable: "--font-mukta",
  subsets: ["latin", "devanagari"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

// Display face for the signature "आहे / नाही" moment - heavy weight,
// condensed width, echoing painted signboard lettering.
const anekDevanagari = Anek_Devanagari({
  variable: "--font-anek",
  subsets: ["latin", "devanagari"],
  weight: ["700", "800"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Naka",
  description: "आपल्या नाक्यावरची विचारणा - who has it, right now.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="mr" className={`${mukta.variable} ${anekDevanagari.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
