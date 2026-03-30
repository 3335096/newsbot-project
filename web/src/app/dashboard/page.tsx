import Link from "next/link";
import { redirect } from "next/navigation";

import { getSessionUser } from "@/lib/session";

export default async function DashboardPage() {
  const session = await getSessionUser();
  if (!session) {
    redirect("/login");
  }
  return (
    <main className="container">
      <h1>NewsBot Web</h1>
      <p className="muted">
        Веб-панель подключена к существующему FastAPI и доступна также как Telegram WebApp.
      </p>
      <p className="muted">
        Пользователь: {session.id} ({session.role})
      </p>

      <section className="card">
        <h2>Разделы</h2>
        <div className="actions">
          <Link className="button button-primary" href="/dashboard/drafts">
            Черновики
          </Link>
          <Link className="button" href="/dashboard/sources">
            Источники
          </Link>
        </div>
      </section>
    </main>
  );
}
