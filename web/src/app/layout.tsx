import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  const displayName = [session?.first_name, session?.last_name].filter(Boolean).join(" ");
  return (
    <html lang="ru">
      <body className="bg-muted/40">
        <div className="min-h-screen">
          <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur">
            <div className="page-container flex items-center justify-between py-3">
              <div className="flex items-center gap-6">
                <strong className="text-base">NewsBot Web</strong>
                {session ? (
                  <nav className="hidden items-center gap-4 md:flex">
                    <Link href="/dashboard">Дашборд</Link>
                    <Link href="/dashboard/sources">Источники</Link>
                    <Link href="/dashboard/publications">Публикации</Link>
                  </nav>
                ) : null}
              </div>
              <div className="flex items-center gap-2">
                {session ? (
                  <>
                    <Badge variant="secondary" className="hidden md:inline-flex">
                      {displayName ? `${displayName} · ` : ""}#{session.id}
                    </Badge>
                    <Badge variant={session.role === "admin" ? "default" : "outline"}>
                      {session.role}
                    </Badge>
                    <form action={logoutAction}>
                      <Button type="submit" variant="outline" size="sm">
                        Выйти
                      </Button>
                    </form>
                  </>
                ) : (
                  <Button asChild size="sm">
                    <Link href="/login">Войти</Link>
                  </Button>
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
