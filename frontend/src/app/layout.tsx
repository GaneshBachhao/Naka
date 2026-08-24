import type { Metadata } from "next";
import { Noto_Sans, Noto_Sans_Devanagari } from "next/font/google";
import "./globals.css";

// Noto Sans has no Devanagari coverage, so it's paired with Noto Sans
// Devanagari and combined into one fallback stack in globals.css - the
// browser resolves each glyph from whichever font actually covers it.
const notoSans = Noto_Sans({
  variable: "--font-noto-sans-latin",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const notoSansDevanagari = Noto_Sans_Devanagari({
  variable: "--font-noto-sans-devanagari",
  subsets: ["devanagari"],
  weight: ["400", "500", "600", "700"],
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
    <html lang="mr" className={`${notoSans.variable} ${notoSansDevanagari.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
