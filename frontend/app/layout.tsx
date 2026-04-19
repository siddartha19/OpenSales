import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SalesOS — AI Sales Team",
  description: "VP Sales + SDR + AE — multi-agent outbound on LangGraph supervisor.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
