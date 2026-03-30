import Link from "next/link";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

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

async function createSource(formData: FormData): Promise<void> {
  "use server";
  const session = await getSessionUser();
  if (!session || session.role !== "admin") {
    throw new Error("Only admins can create sources");
  }
  const name = String(formData.get("name") ?? "").trim();
  const type = String(formData.get("type") ?? "rss").trim();
  const url = String(formData.get("url") ?? "").trim();
  const scheduleCronRaw = String(formData.get("schedule_cron") ?? "").trim();
  const targetLanguage = String(formData.get("default_target_language") ?? "ru").trim();
  const enabled = String(formData.get("enabled") ?? "on") === "on";
  const translateEnabled = String(formData.get("translate_enabled") ?? "on") === "on";

  if (!name || !url || !type) {
    throw new Error("name, type, url are required");
  }

  const response = await fetch(`${env.backendBaseUrl}/api/sources`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name,
      type,
      url,
      enabled,
      schedule_cron: scheduleCronRaw || null,
      translate_enabled: translateEnabled,
      default_target_language: targetLanguage || "ru",
    }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await response.text().catch(() => "Failed to create source"));
  }
  revalidatePath("/dashboard/sources");
}

async function updateSource(formData: FormData): Promise<void> {
  "use server";
  const session = await getSessionUser();
  if (!session || session.role !== "admin") {
    throw new Error("Only admins can update sources");
  }
  const sourceId = Number(formData.get("source_id"));
  const name = String(formData.get("name") ?? "").trim();
  const scheduleCronRaw = String(formData.get("schedule_cron") ?? "").trim();
  const targetLanguage = String(formData.get("default_target_language") ?? "ru").trim();
  const enabled = String(formData.get("enabled") ?? "") === "on";
  const translateEnabled = String(formData.get("translate_enabled") ?? "") === "on";

  if (!sourceId || !name) {
    throw new Error("source_id and name are required");
  }

  const response = await fetch(`${env.backendBaseUrl}/api/sources/${sourceId}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name,
      enabled,
      translate_enabled: translateEnabled,
      schedule_cron: scheduleCronRaw || null,
      default_target_language: targetLanguage || "ru",
    }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await response.text().catch(() => "Failed to update source"));
  }
  revalidatePath("/dashboard/sources");
}

async function deleteSource(formData: FormData): Promise<void> {
  "use server";
  const session = await getSessionUser();
  if (!session || session.role !== "admin") {
    throw new Error("Only admins can delete sources");
  }
  const sourceId = Number(formData.get("source_id"));
  if (!sourceId) {
    throw new Error("source_id is required");
  }
  const response = await fetch(`${env.backendBaseUrl}/api/sources/${sourceId}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await response.text().catch(() => "Failed to delete source"));
  }
  revalidatePath("/dashboard/sources");
}

async function parseNow(formData: FormData): Promise<void> {
  "use server";
  const session = await getSessionUser();
  if (!session) {
    throw new Error("Unauthorized");
  }
  const sourceId = Number(formData.get("source_id"));
  if (!sourceId) {
    throw new Error("source_id is required");
  }
  const response = await fetch(`${env.backendBaseUrl}/api/sources/${sourceId}/parse-now`, {
    method: "POST",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await response.text().catch(() => "Failed to parse source"));
  }
  revalidatePath("/dashboard/sources");
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
      {session.role === "admin" ? (
        <section className="card">
          <h2>Добавить источник</h2>
          <form action={createSource}>
            <div className="form-grid">
              <div>
                <label>Название</label>
                <input name="name" type="text" required />
              </div>
              <div>
                <label>Тип</label>
                <select name="type" defaultValue="rss">
                  <option value="rss">rss</option>
                  <option value="site">site</option>
                </select>
              </div>
              <div>
                <label>URL</label>
                <input name="url" type="url" required />
              </div>
              <div>
                <label>Cron</label>
                <input name="schedule_cron" type="text" placeholder="*/30 * * * *" />
              </div>
              <div>
                <label>Язык по умолчанию</label>
                <input name="default_target_language" type="text" defaultValue="ru" />
              </div>
            </div>
            <div className="row">
              <label className="checkbox">
                <input name="enabled" type="checkbox" defaultChecked />
                enabled
              </label>
              <label className="checkbox">
                <input name="translate_enabled" type="checkbox" defaultChecked />
                translate_enabled
              </label>
            </div>
            <button type="submit">Создать</button>
          </form>
        </section>
      ) : null}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th align="left">ID</th>
              <th align="left">Название</th>
              <th align="left">Тип</th>
              <th align="left">URL</th>
              <th align="left">Включен</th>
              <th align="left">Перевод</th>
              <th align="left">Cron</th>
              <th align="left">Язык</th>
              <th align="left">Действия</th>
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
                <td>{source.translate_enabled ? "yes" : "no"}</td>
                <td>{source.schedule_cron || "-"}</td>
                <td>{source.default_target_language}</td>
                <td>
                  <form action={parseNow} style={{ display: "inline-block", marginRight: 8 }}>
                    <input type="hidden" name="source_id" value={source.id} />
                    <button type="submit">Parse now</button>
                  </form>
                  {session.role === "admin" ? (
                    <details>
                      <summary>Edit</summary>
                      <form action={updateSource}>
                        <input type="hidden" name="source_id" value={source.id} />
                        <label>Название</label>
                        <input name="name" type="text" defaultValue={source.name} required />
                        <label>Cron</label>
                        <input
                          name="schedule_cron"
                          type="text"
                          defaultValue={source.schedule_cron || ""}
                        />
                        <label>Язык</label>
                        <input
                          name="default_target_language"
                          type="text"
                          defaultValue={source.default_target_language}
                        />
                        <div className="row">
                          <label className="checkbox">
                            <input name="enabled" type="checkbox" defaultChecked={source.enabled} />
                            enabled
                          </label>
                          <label className="checkbox">
                            <input
                              name="translate_enabled"
                              type="checkbox"
                              defaultChecked={source.translate_enabled}
                            />
                            translate_enabled
                          </label>
                        </div>
                        <button type="submit">Сохранить</button>
                      </form>
                      <form action={deleteSource}>
                        <input type="hidden" name="source_id" value={source.id} />
                        <button type="submit" className="button danger">
                          Удалить
                        </button>
                      </form>
                    </details>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
