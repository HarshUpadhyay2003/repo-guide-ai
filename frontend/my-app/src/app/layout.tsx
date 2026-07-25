import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "../components/layout/Navbar";
import { Footer } from "../components/layout/Footer";
import { FeedbackProvider } from "../context/FeedbackContext";
import { FeedbackModal } from "../components/feedback/FeedbackModal";
import { ReportAIIssueModal } from "../components/feedback/ReportAIIssueModal";
import { FeedbackToast } from "../components/feedback/FeedbackToast";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://repo-guide-ai.vercel.app"),
  title: {
    default: "RepoPilot",
    template: "%s | RepoPilot",
  },
  description: "AI-powered repository onboarding for open-source contributors.",
  keywords: [
    "RepoPilot",
    "GitHub",
    "Open Source",
    "Repository Analysis",
    "Issue Analysis",
    "Contribution Guide",
    "Developer Tools",
    "AI"
  ],
  icons: {
    icon: "/logos/repo_pilot_icon_no_background.svg",
    shortcut: "/logos/repo_pilot_icon_no_background.svg",
    apple: "/logos/repo_pilot_icon_no_background.svg",
  },
  openGraph: {
    title: "RepoPilot",
    description: "AI-powered repository onboarding for open-source contributors.",
    url: "https://repo-guide-ai.vercel.app",
    siteName: "RepoPilot",
    images: [
      {
        url: "/logos/repo_pilot_dark_logo.png",
        width: 541,
        height: 382,
        alt: "RepoPilot Logo",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "RepoPilot",
    description: "AI-powered repository onboarding for open-source contributors.",
    images: ["/logos/repo_pilot_dark_logo.png"],
  },
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
      <body className="min-h-full flex flex-col bg-background text-text-secondary font-sans">
        <FeedbackProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
          <Footer />
          <FeedbackModal />
          <ReportAIIssueModal />
          <FeedbackToast />
        </FeedbackProvider>
      </body>
    </html>
  );
}

