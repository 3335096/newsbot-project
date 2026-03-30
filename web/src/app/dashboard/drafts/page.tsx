import Link from "next/link";
import { redirect } from "next/navigation";

import { env } from "@/lib/env";
import { getSessionUser } from "@/lib/session";
import type { DraftOut } from "@/lib/types";
import { revalidatePath } from "next/cache";

async function loadDrafts(): Promise<DraftOut[]> {
  const response = await fetch(`${env.backendBaseUrl}/api/drafts`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch drafts (${response.status})`);
  }
  return (await response.json()) as DraftOut[];
}

async function approveDraft(draftId: number): Promise<void> {
  "use server";
  await fetch(`${env.backendBaseUrl}/api/drafts/${draftId}/approve`, {
    method: "POST",
    cache: "no-store",
  });
  revalidatePath("/dashboard/drafts");
}

async function rejectDraft(formData: FormData): Promise<void> {
  "use server";
  const draftId = Number(formData.get("draftId"));
  const reason = String(formData.get("reason") ?? "").trim() || "Rejected from web panel";
  await fetch(`${env.backendBaseUrl}/api/drafts/${draftId}/reject`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ reason }),
    cache: "no-store",
  });
  revalidatePath("/dashboard/drafts");
}

export default async function DraftsPage() {
  const user = await getSessionUser();
  if (!user) {
    redirect("/login");
  }

  const drafts = await loadDrafts();

  return (
    <main className="container">
      <h1>Черновики</h1>
      <p>Всего: {drafts.length}</p>
      <p>
        <Link href="/dashboard">Назад в дашборд</Link>
      </p>
      {drafts.length === 0 ? (
        <p>Черновиков пока нет.</p>
      ) : (
        drafts.map((draft) => (
          <article key={draft.id} className="card">
            <h2>
              #{draft.id} — {draft.title_translated || draft.title_original || "Без заголовка"}
            </h2>
            <p>
              <strong>Статус:</strong> {draft.status}
            </p>
            <p>
              <strong>Язык:</strong> {draft.source_language || "?"} → {draft.target_language}
            </p>
            <p>{(draft.content_translated || draft.content_original || "").slice(0, 400)}</p>
            <form
              action={approveDraft.bind(null, draft.id)}
              style={{ display: "inline-block", marginRight: 8 }}
            >
              <button type="submit">Одобрить</button>
            </form>
            <form action={rejectDraft} style={{ display: "inline-block" }}>
              <input type="hidden" name="draftId" value={draft.id} />
              <input type="text" name="reason" placeholder="Причина отклонения" />
              <button type="submit">Отклонить</button>
            </form>
          </article>
        ))
      )}
    </main>
  );
}
