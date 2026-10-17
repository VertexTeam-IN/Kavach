import { DM_Mono, Manrope, Space_Grotesk } from "next/font/google";

import "./globals.css";

// Self-hosted at build time by next/font (no runtime request to Google).
const display = Space_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--kv-display",
});
const body = Manrope({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--kv-body",
});
const mono = DM_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--kv-mono" });

export const metadata = {
  title: "Kavach — Passwordless sign-in",
  description: "Sign in to any website with your fingerprint, face or device PIN.",
};

export const viewport = { themeColor: "#ffffff" };

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
