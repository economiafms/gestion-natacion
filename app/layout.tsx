import type { Metadata, Viewport } from "next";
import { Inter, Oswald } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const oswald = Oswald({
  variable: "--font-heading",
  weight: ["500", "600", "700"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Complejo Acuático | Newell's Old Boys",
  description:
    "Plataforma de nadadores del Complejo Acuático de Newell's Old Boys: rutinas, tiempos, torneos y ranking del club.",
};

export const viewport: Viewport = {
  themeColor: "#0f1015",
  colorScheme: "dark",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      className={`dark ${inter.variable} ${oswald.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {children}
        <Toaster theme="dark" />
      </body>
    </html>
  );
}
