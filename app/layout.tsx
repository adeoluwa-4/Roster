import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const image = `${protocol}://${host}/og.png`;
  return {
    title: "ROSTER — Daily NBA Athlete Guessing Game",
    description: "Guess the mystery NBA athlete in ten tries using career clues, teams, height, nationality, and more.",
    applicationName: "ROSTER",
    keywords: ["NBA", "basketball", "daily game", "athlete trivia", "guessing game"],
    openGraph: { title: "ROSTER — Know the player", description: "One mystery NBA athlete. Six clues per guess. Ten shots to find the name.", type: "website", images: [{ url: image, width: 1733, height: 909, alt: "ROSTER — Know the player" }] },
    twitter: { card: "summary_large_image", title: "ROSTER — Know the player", description: "One mystery NBA athlete. Six clues per guess. Ten shots to find the name.", images: [image] },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
