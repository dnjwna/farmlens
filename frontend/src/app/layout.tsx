import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "FarmLens",
  description: "Platform AI untuk petani kecil Indonesia",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id">
      <body>
        <Toaster position="top-center" />
        {children}
      </body>
    </html>
  );
}