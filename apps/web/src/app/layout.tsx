import type { Metadata } from "next";
import dynamic from "next/dynamic";
import { Nunito, Source_Code_Pro } from "next/font/google";
import "./globals.css";

const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"],
});

const sourceCodePro = Source_Code_Pro({
  variable: "--font-mono",
  subsets: ["latin"],
});

import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";

// Lazy-load non-critical root components — reduces initial JS bundle
const SmoothScroll = dynamic(
  () => import("@/components/layout/smooth-scroll").then((m) => m.SmoothScroll),
);
const CommandPalette = dynamic(
  () => import("@/features/command/components/CommandPalette").then((m) => m.CommandPalette),
);

export const metadata: Metadata = {
  title: "SCHALE Office",
  description: "Federal Investigation Club S.C.H.A.L.E",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${nunito.variable} ${sourceCodePro.variable} antialiased h-screen w-screen overflow-hidden bg-background text-foreground`}
      >
        <TooltipProvider>
          <a href="#main-content" className="skip-to-content">
            Skip to main content
          </a>
          <SmoothScroll />
          <CommandPalette />
          <Toaster />
          {children}
        </TooltipProvider>
      </body>
    </html>
  );
}
