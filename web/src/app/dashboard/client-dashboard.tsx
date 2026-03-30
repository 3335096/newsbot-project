"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import type { DraftOut, PublicationOut, SessionUser } from "@/lib/types";

type TabKey = "drafts" | "sources" | "publications";

type Props = {
  initialSession: SessionUser;
  initialDrafts: DraftOut[];
  initialPublications: PublicationOut[];
};

type Toast = {
  id: number;
  kind: "success" | "error" | "info";
  message: string;
};

type PublicationCreatePayload = {
  draft_id: number;
  channel: string;
  publish_now: boolean;
  scheduled_at?: string | null;
};

type LlmTaskType = "summary" | "rewrite" | "title_hashtags";

const TASK_TYPE_TO_PRESET: Record<LlmTaskType, string> = {
  summary: "summary",
  rewrite: "rewrite_style",
  title_hashtags: "title_hashtags",
};

const POLL_INTERVAL_MS = 1000;
const POLL_ATTEMPTS = 12;

function humanizeDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export default function ClientDashboard({
  initialSession,
  initialDrafts,
  initialPublications,
}: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>("drafts");
  const [drafts, setDrafts] = useState<DraftOut[]>(initialDrafts);
  const [publications, setPublications] = useState<PublicationOut[]>(initialPublications);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [pubDraftId, setPubDraftId] = useState<number>(initialDrafts[0]?.id ?? 0);
  const [pubChannel, setPubChannel] = useState<string>("");
  const [pubNow, setPubNow] = useState<boolean>(true);
  const [pubScheduleAt, setPubScheduleAt] = useState<string>("");
  const [rejectReasonByDraft, setRejectReasonByDraft] = useState<Record<number, string>>({});
  const [llmTaskTypeByDraft, setLlmTaskTypeByDraft] = useState<
    Record<number, LlmTaskType>
  >({});
  const [llmModelByDraft, setLlmModelByDraft] = useState<Record<number, string>>({});
  const [llmMaxLenByDraft, setLlmMaxLenByDraft] = useState<Record<number, number>>({});
  const [llmResultByDraft, setLlmResultByDraft] = useState<Record<number, string>>({});

  const pushToast = (kind: Toast["kind"], message: string) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev, { id, kind, message }]);
  };

  useEffect(() => {
    if (toasts.length === 0) {
      return;
    }
    const timer = setTimeout(() => {
      setToasts((prev) => prev.slice(1));
    }, 2600);
    return () => clearTimeout(timer);
  }, [toasts]);

  const callBackend = async <T,>(
    path: string,
    init?: RequestInit,
    errorTitle = "Operation failed",
  ): Promise<T> => {
    const response = await fetch(`/api/backend/${path.replace(/^\/+/, "")}`, {
      cache: "no-store",
      ...init,
    });
    const text = await response.text();
    let parsed: unknown = null;
    try {
      parsed = text ? (JSON.parse(text) as unknown) : null;
    } catch {
      parsed = text;
    }
    if (!response.ok) {
      const detail =
        typeof parsed === "object" && parsed && "detail" in parsed
          ? String((parsed as { detail?: string }).detail || errorTitle)
          : `${errorTitle} (${response.status})`;
      throw new Error(detail);
    }
    return (parsed as T) ?? ({} as T);
  };

  const refreshDrafts = async () => {
    const data = await callBackend<DraftOut[]>("api/drafts");
    setDrafts(data);
  };

  const refreshPublications = async () => {
    const data = await callBackend<PublicationOut[]>("api/publications?limit=100");
    setPublications(data);
  };

  const withBusy = async (fn: () => Promise<void>) => {
    if (isBusy) {
      return;
    }
    setIsBusy(true);
    try {
      await fn();
    } finally {
      setIsBusy(false);
    }
  };

  const handleApproveDraft = async (draftId: number) =>
    withBusy(async () => {
      await callBackend(`api/drafts/${draftId}/approve`, { method: "POST" }, "Approve failed");
      await refreshDrafts();
      pushToast("success", `Draft #${draftId} approved`);
    });

  const handleRejectDraft = async (draftId: number) =>
    withBusy(async () => {
      const reason = (rejectReasonByDraft[draftId] || "").trim();
      if (!reason) {
        pushToast("error", "Укажите причину отклонения");
        return;
      }
      await callBackend(
        `api/drafts/${draftId}/reject`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ reason }),
        },
        "Reject failed",
      );
      await refreshDrafts();
      setRejectReasonByDraft((prev) => ({ ...prev, [draftId]: "" }));
      pushToast("success", `Draft #${draftId} rejected`);
    });

  const handleRunLlm = async (draftId: number) =>
    withBusy(async () => {
      const taskType = llmTaskTypeByDraft[draftId] || "summary";
      const preset = TASK_TYPE_TO_PRESET[taskType];
      const payload = {
        draft_id: draftId,
        task_type: taskType,
        preset,
        model: (llmModelByDraft[draftId] || "").trim() || undefined,
        max_len: llmMaxLenByDraft[draftId] || 700,
      };
      const task = await callBackend<{ id: number; status: string }>(
        "api/llm/tasks",
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
        },
        "LLM task create failed",
      );
      pushToast("info", `LLM task #${task.id} queued (${task.status})`);
      let resultText = "";
      for (let i = 0; i < POLL_ATTEMPTS; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
        const current = await callBackend<{ status: string; result?: string | null; error?: string | null }>(
          `api/llm/tasks/${task.id}`,
        );
        if (current.status === "success") {
          resultText = current.result || "";
          pushToast("success", `LLM task #${task.id} completed`);
          break;
        }
        if (current.status === "error") {
          throw new Error(current.error || `LLM task #${task.id} failed`);
        }
      }
      if (resultText) {
        setLlmResultByDraft((prev) => ({ ...prev, [draftId]: resultText }));
      }
      await refreshDrafts();
    });

  const handleCreatePublication = async () =>
    withBusy(async () => {
      if (!pubDraftId || !pubChannel.trim()) {
        pushToast("error", "Укажите draft_id и channel alias");
        return;
      }
      const payload: PublicationCreatePayload = {
        draft_id: pubDraftId,
        channel: pubChannel.trim(),
        publish_now: pubNow,
      };
      if (!pubNow && pubScheduleAt) {
        payload.scheduled_at = new Date(pubScheduleAt).toISOString();
      }
      const publication = await callBackend<PublicationOut>(
        "api/publications",
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
        },
        "Create publication failed",
      );
      pushToast("success", `Publication #${publication.id} created (${publication.status})`);
      await refreshPublications();
    });

  const handleRetryPublication = async (publicationId: number) =>
    withBusy(async () => {
      const updated = await callBackend<PublicationOut>(
        `api/publications/${publicationId}/retry`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ force: true }),
        },
        "Retry publication failed",
      );
      pushToast("success", `Publication #${updated.id} retried (${updated.status})`);
      await refreshPublications();
    });

  const handleRequeueFailedPublication = async (publicationId: number) =>
    withBusy(async () => {
      const updated = await callBackend<PublicationOut>(
        `api/publications/${publicationId}/requeue-failed`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ force: true }),
        },
        "Requeue failed publication failed",
      );
      pushToast("success", `Publication #${updated.id} requeued (${updated.status})`);
      await refreshPublications();
    });

  const renderDrafts = () => (
    <section className="card">
      <h2>Черновики + LLM</h2>
      <p className="muted">Одобрение/отклонение и запуск LLM-задач прямо из веба.</p>
      <div className="stack">
        {drafts.length === 0 ? (
          <p>Черновиков пока нет.</p>
        ) : (
          drafts.map((draft) => (
            <article key={draft.id} className="card">
              <h3>
                #{draft.id} — {draft.title_translated || draft.title_original || "Без заголовка"}
              </h3>
              <p className="muted">
                status: <b>{draft.status}</b> | lang: {draft.source_language || "?"} → {draft.target_language}
              </p>
              <p>{(draft.content_translated || draft.content_original || "").slice(0, 300)}</p>

              <div className="draft-actions">
                <button type="button" onClick={() => void handleApproveDraft(draft.id)} disabled={isBusy}>
                  Одобрить
                </button>
                <input
                  className="draft-reject-input"
                  type="text"
                  placeholder="Причина отклонения"
                  value={rejectReasonByDraft[draft.id] || ""}
                  onChange={(event) =>
                    setRejectReasonByDraft((prev) => ({ ...prev, [draft.id]: event.target.value }))
                  }
                />
                <button type="button" onClick={() => void handleRejectDraft(draft.id)} disabled={isBusy}>
                  Отклонить
                </button>
              </div>

              <div className="form-grid">
                <div>
                  <label>LLM задача</label>
                  <select
                    value={llmTaskTypeByDraft[draft.id] || "summary"}
                    onChange={(event) =>
                      setLlmTaskTypeByDraft((prev) => ({
                        ...prev,
                        [draft.id]: event.target.value as LlmTaskType,
                      }))
                    }
                  >
                    <option value="summary">summary</option>
                    <option value="rewrite">rewrite</option>
                    <option value="title_hashtags">title_hashtags</option>
                  </select>
                </div>
                <div>
                  <label>Model (опционально)</label>
                  <input
                    type="text"
                    placeholder="openai/gpt-4o-mini"
                    value={llmModelByDraft[draft.id] || ""}
                    onChange={(event) =>
                      setLlmModelByDraft((prev) => ({ ...prev, [draft.id]: event.target.value }))
                    }
                  />
                </div>
                <div>
                  <label>max_len</label>
                  <input
                    type="number"
                    min={100}
                    max={4000}
                    value={llmMaxLenByDraft[draft.id] || 700}
                    onChange={(event) =>
                      setLlmMaxLenByDraft((prev) => ({
                        ...prev,
                        [draft.id]: Number(event.target.value) || 700,
                      }))
                    }
                  />
                </div>
              </div>
              <button type="button" onClick={() => void handleRunLlm(draft.id)} disabled={isBusy}>
                Запустить LLM
              </button>
              {llmResultByDraft[draft.id] ? (
                <pre className="result-box">{llmResultByDraft[draft.id]}</pre>
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  );

  const renderSources = () => (
    <section className="card">
      <h2>Источники</h2>
      <p className="muted">
        Полный CRUD для источников открыт на отдельной странице:{" "}
        <Link href="/dashboard/sources">/dashboard/sources</Link>
      </p>
      <p className="muted">
        Текущая роль: <b>{initialSession.role}</b> (управление источниками доступно на отдельной странице)
      </p>
    </section>
  );

  const renderPublications = () => (
    <section className="card">
      <h2>Публикации</h2>
      <p className="muted">Создание публикации и операционные retry/requeue действия.</p>

      <section className="card">
        <h3>Создать публикацию</h3>
        <div className="form-grid">
          <div>
            <label>Draft ID</label>
            <input
              type="number"
              min={1}
              value={pubDraftId || ""}
              onChange={(event) => setPubDraftId(Number(event.target.value) || 0)}
            />
          </div>
          <div>
            <label>Channel alias</label>
            <input
              type="text"
              placeholder="main"
              value={pubChannel}
              onChange={(event) => setPubChannel(event.target.value)}
            />
          </div>
          <div>
            <label>Режим</label>
            <select value={pubNow ? "now" : "scheduled"} onChange={(event) => setPubNow(event.target.value === "now")}>
              <option value="now">publish_now=true</option>
              <option value="scheduled">scheduled</option>
            </select>
          </div>
          <div>
            <label>scheduled_at (local datetime)</label>
            <input
              type="datetime-local"
              value={pubScheduleAt}
              onChange={(event) => setPubScheduleAt(event.target.value)}
              disabled={pubNow}
            />
          </div>
        </div>
        <button type="button" onClick={() => void handleCreatePublication()} disabled={isBusy}>
          Создать публикацию
        </button>
      </section>

      <section className="card">
        <h3>Последние публикации</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>draft_id</th>
              <th>channel</th>
              <th>status</th>
              <th>scheduled_at</th>
              <th>published_at</th>
              <th>actions</th>
            </tr>
          </thead>
          <tbody>
            {publications.map((publication) => (
              <tr key={publication.id}>
                <td>{publication.id}</td>
                <td>{publication.draft_id ?? "-"}</td>
                <td>{publication.channel_alias || publication.channel_id || "-"}</td>
                <td>{publication.status}</td>
                <td>{humanizeDate(publication.scheduled_at)}</td>
                <td>{humanizeDate(publication.published_at)}</td>
                <td>
                  <div className="actions">
                    <button
                      type="button"
                      onClick={() => void handleRetryPublication(publication.id)}
                      disabled={isBusy}
                    >
                      Retry
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleRequeueFailedPublication(publication.id)}
                      disabled={isBusy}
                    >
                      Requeue failed
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );

  return (
    <main className="container">
      <h1>NewsBot Web</h1>
      <p className="muted">
        Пользователь: #{initialSession.id} ({initialSession.role})
      </p>

      <section className="card">
        <div className="actions">
          <button
            type="button"
            className={activeTab === "drafts" ? "button-primary" : ""}
            onClick={() => setActiveTab("drafts")}
          >
            Черновики + LLM
          </button>
          <button
            type="button"
            className={activeTab === "sources" ? "button-primary" : ""}
            onClick={() => setActiveTab("sources")}
          >
            Источники
          </button>
          <button
            type="button"
            className={activeTab === "publications" ? "button-primary" : ""}
            onClick={() => setActiveTab("publications")}
          >
            Публикации
          </button>
        </div>
      </section>

      {activeTab === "drafts" ? renderDrafts() : null}
      {activeTab === "sources" ? renderSources() : null}
      {activeTab === "publications" ? renderPublications() : null}

      <div className="toast-stack">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast-${toast.kind}`}>
            {toast.message}
          </div>
        ))}
      </div>
    </main>
  );
}
