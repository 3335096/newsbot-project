import Link from "next/link";
import { redirect } from "next/navigation";

import { env } from "@/lib/env";
import { getSessionUser } from "@/lib/session";
import type { PublicationOut } from "@/lib/types";

async function fetchPublications(): Promise<PublicationOut[]> {
  const response = await fetch(`${env.backendBaseUrl}/api/publications?limit=200`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Unable to load publications: ${response.status}`);
  }
  return (await response.json()) as PublicationOut[];
}

export default async function PublicationsPage() {
  const session = await getSessionUser();
  if (!session) {
    redirect("/login");
  }

  const publications = await fetchPublications();

  return (
    <main className="container">
      <div className="row space-between">
        <h1>Публикации</h1>
        <Link href="/dashboard">Назад к панели</Link>
      </div>
      <p className="muted">Сводный список публикаций (последние 200).</p>
      <section className="card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>draft_id</th>
              <th>channel</th>
              <th>status</th>
              <th>scheduled_at</th>
              <th>published_at</th>
              <th>log</th>
            </tr>
          </thead>
          <tbody>
            {publications.map((publication) => (
              <tr key={publication.id}>
                <td>{publication.id}</td>
                <td>{publication.draft_id ?? "-"}</td>
                <td>{publication.channel_alias || publication.channel_id || "-"}</td>
                <td>{publication.status}</td>
                <td>{publication.scheduled_at || "-"}</td>
                <td>{publication.published_at || "-"}</td>
                <td>{publication.log || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
