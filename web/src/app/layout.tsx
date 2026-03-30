import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NewsBot Web",
  description: "Web dashboard for NewsBot",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>
        <div className="layout-shell">
          <header className="layout-header">
            <div className="container">
              <strong>NewsBot Web</strong>
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
