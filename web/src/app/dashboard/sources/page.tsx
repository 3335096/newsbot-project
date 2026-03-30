import Link from "next/link";
import { redirect } from "next/navigation";

import { env } from "@/lib/env";
import { getSessionUser } from "@/lib/session";
import type { SourceOut } from "@/lib/types";

async function fetchSources(): Promise<SourceOut[]> {
  const response = await fetch(`${env.backendBaseUrl}/api/sources`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Unable to load sources: ${response.status}`);
  }
  return (await response.json()) as SourceOut[];
}

export default async function SourcesPage() {
  const session = await getSessionUser();
  if (!session) {
    redirect("/login");
  }

  const sources = await fetchSources();

  return (
    <main className="container">
      <div className="row space-between">
        <h1>Источники</h1>
        <Link href="/dashboard">Назад к панели</Link>
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th align="left">ID</th>
              <th align="left">Название</th>
              <th align="left">Тип</th>
              <th align="left">URL</th>
              <th align="left">Включен</th>
              <th align="left">Cron</th>
              <th align="left">Язык</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id}>
                <td>{source.id}</td>
                <td>{source.name}</td>
                <td>{source.type}</td>
                <td>
                  <a href={source.url} target="_blank" rel="noreferrer">
                    {source.url}
                  </a>
                </td>
                <td>{source.enabled ? "yes" : "no"}</td>
                <td>{source.schedule_cron || "-"}</td>
                <td>{source.default_target_language}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
