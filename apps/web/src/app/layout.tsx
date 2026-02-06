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
        className={`${nunito.variable} ${sourceCodePro.variable} antialiased bg-[#f3f7f9] text-slate-700`}
      >
        {children}
      </body>
    </html>
  );
}
