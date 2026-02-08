import type { Metadata } from "next";
import { Nunito, Source_Code_Pro } from "next/font/google";
import "./globals.css";

const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
  weight: ["400", "600", "700", "800"], // BA uses heavy weights often
});

const sourceCodePro = Source_Code_Pro({
  variable: "--font-mono",
  subsets: ["latin"],
});

import { ThemeProvider } from "@/components/providers/theme-provider";
import { SmoothScroll } from "@/components/layout/smooth-scroll";
import { TooltipProvider } from "@/components/ui/tooltip";
import { CommandPalette } from "@/components/features/command/CommandPalette";
import { Toaster } from "@/components/ui/toaster";

export const metadata: Metadata = {
  title: "Arona | SCHALE Office",
  description: "Federal Investigation Club S.C.H.A.L.E",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${nunito.variable} ${sourceCodePro.variable} antialiased h-screen w-screen overflow-hidden bg-background text-foreground`}
      >
        <ThemeProvider>
          <TooltipProvider>
            <a href="#main-content" className="skip-to-content">
              Skip to main content
            </a>
            <SmoothScroll />
            <CommandPalette />
            <Toaster />
            {children}
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
