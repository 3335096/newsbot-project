import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { clearSessionCookie, getSessionUser } from "@/lib/session";
import "./globals.css";

export const metadata: Metadata = {
  title: "NewsBot Web",
  description: "Web dashboard for NewsBot",
};

async function logoutAction() {
  "use server";
  await clearSessionCookie();
  redirect("/login");
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getSessionUser();
  return (
    <html lang="ru">
      <body>
        <div className="layout-shell">
          <header className="layout-header">
            <div className="container row space-between">
              <div className="row">
                <strong>NewsBot Web</strong>
                {session ? (
                  <nav className="row">
                    <Link href="/dashboard">Дашборд</Link>
                    <Link href="/dashboard/drafts">Черновики</Link>
                    <Link href="/dashboard/sources">Источники</Link>
                  </nav>
                ) : null}
              </div>
              <div className="row">
                {session ? (
                  <>
                    <span className="muted">
                      #{session.id} ({session.role})
                    </span>
                    <form action={logoutAction}>
                      <button type="submit" className="button">
                        Выйти
                      </button>
                    </form>
                  </>
                ) : (
                  <Link className="button" href="/login">
                    Войти
                  </Link>
                )}
              </div>
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
