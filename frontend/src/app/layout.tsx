import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  fallback: ["system-ui", "sans-serif"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  fallback: ["ui-monospace", "monospace"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    template: "%s | SelfSmart AI",
    default: "SelfSmart AI — Intelligent Decision Copilot",
  },
  description:
    "AI-powered self-learning assistant that continuously improves through knowledge integration and conversation.",
  keywords: [
    "AI assistant",
    "self-learning",
    "chatbot",
    "LLM",
    "RAG",
    "knowledge base",
    "decision support",
  ],
  authors: [{ name: "SelfSmart Team" }],
  creator: "SelfSmart AI",
  publisher: "SelfSmart AI",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://selfsmart.ai",
    siteName: "SelfSmart AI",
    title: "SelfSmart AI — Intelligent Decision Copilot",
    description:
      "AI-powered self-learning assistant that continuously improves through knowledge integration and conversation.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "SelfSmart AI Dashboard",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "SelfSmart AI",
    description:
      "AI-powered self-learning assistant that continuously improves through knowledge integration and conversation.",
    images: ["/og-image.png"],
    creator: "@selfsmart_ai",
  },
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png",
    apple: "/apple-touch-icon.png",
  },
  manifest: "/site.webmanifest",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#09090b" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://api.selfsmart.ai" />
      </head>
      <body className="min-h-full bg-background text-foreground overflow-hidden">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}