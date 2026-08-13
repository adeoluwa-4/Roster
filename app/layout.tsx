import type { Metadata } from "next";
import { headers } from "next/headers";
import Script from "next/script";
import "./globals.css";

const adsensePublisherId = "ca-pub-6702288023645677";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const image = `${protocol}://${host}/og.png?v=2`;
  return {
    title: "Guess the NBA Player — Daily NBA Guessing Game",
    description: "Guess the mystery NBA athlete in ten tries using career clues, teams, height, nationality, and more.",
    applicationName: "Guess the NBA Player",
    icons: { icon: "/guess-the-athlete-icon.png", shortcut: "/guess-the-athlete-icon.png", apple: "/guess-the-athlete-icon.png" },
    keywords: ["NBA", "basketball", "daily game", "athlete trivia", "guessing game"],
    openGraph: { title: "Guess the NBA Player — Know the player", description: "One mystery NBA athlete. Six clues per guess. Ten shots to find the name.", type: "website", images: [{ url: image, width: 1733, height: 909, alt: "Guess the NBA Player — Know the player" }] },
    twitter: { card: "summary_large_image", title: "Guess the NBA Player — Know the player", description: "One mystery NBA athlete. Six clues per guess. Ten shots to find the name.", images: [image] },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>
    <Script async strategy="afterInteractive" src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${adsensePublisherId}`} crossOrigin="anonymous" />
    {children}
  </body></html>;
}
