import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import { Toaster } from "react-hot-toast";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FarmLens",
  description: "Bantu petani mengenali penyakit tanaman, membaca cuaca lahan, dan melindungi panen.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#15803d",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className={jakarta.variable}>
      <body className="antialiased">
        <div className="mx-auto min-h-dvh w-full max-w-[480px] bg-background shadow-sm">
          {children}
        </div>
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 4000,
            style: { fontSize: "15px", borderRadius: "12px", maxWidth: "420px" },
          }}
        />
      </body>
    </html>
  );
}
