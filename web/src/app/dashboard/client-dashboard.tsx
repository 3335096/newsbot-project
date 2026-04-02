"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
const LIVE_REFRESH_INTERVAL_MS = 5000;

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
  const [draftQuery, setDraftQuery] = useState<string>("");
  const [draftStatusFilter, setDraftStatusFilter] = useState<string>("all");
  const [publicationQuery, setPublicationQuery] = useState<string>("");
  const [publicationStatusFilter, setPublicationStatusFilter] = useState<string>("all");
  const [liveRefreshEnabled, setLiveRefreshEnabled] = useState<boolean>(true);
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

  useEffect(() => {
    if (!liveRefreshEnabled || isBusy) {
      return;
    }
    const hasRunningPublications = publications.some((publication) =>
      ["queued", "running", "scheduled"].includes(publication.status),
    );
    const hasPendingDrafts = drafts.some((draft) => ["new", "flagged"].includes(draft.status));
    if (!hasRunningPublications && !hasPendingDrafts) {
      return;
    }
    const timer = setInterval(() => {
      void refreshDrafts();
      void refreshPublications();
    }, LIVE_REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [liveRefreshEnabled, isBusy, publications, drafts]);

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

  const filteredDrafts = useMemo(() => {
    const q = draftQuery.trim().toLowerCase();
    return drafts.filter((draft) => {
      if (draftStatusFilter !== "all" && draft.status !== draftStatusFilter) {
        return false;
      }
      if (!q) {
        return true;
      }
      const haystack = [
        String(draft.id),
        draft.title_translated || "",
        draft.title_original || "",
        draft.content_translated || "",
        draft.content_original || "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [drafts, draftQuery, draftStatusFilter]);

  const filteredPublications = useMemo(() => {
    const q = publicationQuery.trim().toLowerCase();
    return publications.filter((publication) => {
      if (publicationStatusFilter !== "all" && publication.status !== publicationStatusFilter) {
        return false;
      }
      if (!q) {
        return true;
      }
      const haystack = [
        String(publication.id),
        String(publication.draft_id ?? ""),
        String(publication.channel_alias ?? ""),
        String(publication.channel_id ?? ""),
        publication.status,
        publication.log || "",
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [publications, publicationQuery, publicationStatusFilter]);

  const renderDrafts = () => (
    <Card>
      <CardHeader>
        <CardTitle>Черновики + LLM</CardTitle>
        <CardDescription>Одобрение/отклонение и запуск LLM-задач прямо из веба.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label>Поиск по черновикам</Label>
            <Input
              type="text"
              placeholder="ID, заголовок, фрагмент текста"
              value={draftQuery}
              onChange={(event) => setDraftQuery(event.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label>Фильтр по статусу</Label>
            <Select value={draftStatusFilter} onValueChange={setDraftStatusFilter}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">all</SelectItem>
                <SelectItem value="new">new</SelectItem>
                <SelectItem value="flagged">flagged</SelectItem>
                <SelectItem value="approved">approved</SelectItem>
                <SelectItem value="rejected">rejected</SelectItem>
                <SelectItem value="published">published</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="stack">
          {filteredDrafts.length === 0 ? (
            <p className="text-sm text-muted-foreground">По выбранным фильтрам черновиков не найдено.</p>
          ) : (
            filteredDrafts.map((draft) => (
              <Card key={draft.id} className="py-4">
                <CardHeader className="pb-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle className="text-base">
                      #{draft.id} — {draft.title_translated || draft.title_original || "Без заголовка"}
                    </CardTitle>
                    <Badge variant="secondary">{draft.status}</Badge>
                    <Badge variant="outline">
                      {draft.source_language || "?"} → {draft.target_language}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-4">
                  <p className="text-sm text-muted-foreground">
                    {(draft.content_translated || draft.content_original || "").slice(0, 300)}
                  </p>

                  <div className="flex flex-wrap gap-2">
                    <Button type="button" onClick={() => void handleApproveDraft(draft.id)} disabled={isBusy}>
                      Одобрить
                    </Button>
                    <Input
                      className="min-w-[220px] max-w-md"
                      type="text"
                      placeholder="Причина отклонения"
                      value={rejectReasonByDraft[draft.id] || ""}
                      onChange={(event) =>
                        setRejectReasonByDraft((prev) => ({ ...prev, [draft.id]: event.target.value }))
                      }
                    />
                    <Button
                      type="button"
                      variant="destructive"
                      onClick={() => {
                        if (!window.confirm(`Подтвердить отклонение draft #${draft.id}?`)) {
                          return;
                        }
                        void handleRejectDraft(draft.id);
                      }}
                      disabled={isBusy}
                    >
                      Отклонить
                    </Button>
                  </div>

                  <div className="grid gap-3 md:grid-cols-3">
                    <div className="grid gap-2">
                      <Label>LLM задача</Label>
                      <Select
                        value={llmTaskTypeByDraft[draft.id] || "summary"}
                        onValueChange={(value) =>
                          setLlmTaskTypeByDraft((prev) => ({
                            ...prev,
                            [draft.id]: value as LlmTaskType,
                          }))
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="summary">summary</SelectItem>
                          <SelectItem value="rewrite">rewrite</SelectItem>
                          <SelectItem value="title_hashtags">title_hashtags</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid gap-2">
                      <Label>Model (опционально)</Label>
                      <Input
                        type="text"
                        placeholder="openai/gpt-4o-mini"
                        value={llmModelByDraft[draft.id] || ""}
                        onChange={(event) =>
                          setLlmModelByDraft((prev) => ({ ...prev, [draft.id]: event.target.value }))
                        }
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>max_len</Label>
                      <Input
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
                  <Button type="button" onClick={() => void handleRunLlm(draft.id)} disabled={isBusy}>
                    Запустить LLM
                  </Button>
                  {llmResultByDraft[draft.id] ? (
                    <pre className="result-box">{llmResultByDraft[draft.id]}</pre>
                  ) : null}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );

  const renderSources = () => (
    <Card>
      <CardHeader>
        <CardTitle>Источники</CardTitle>
        <CardDescription>CRUD для источников вынесен на отдельный экран.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">
        <p className="text-sm text-muted-foreground">
          Текущая роль: <b>{initialSession.role}</b>
        </p>
        <div className="flex flex-wrap gap-2">
          <Button asChild>
            <Link href="/dashboard/sources">Открыть /dashboard/sources</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/dashboard/publications">Перейти в публикации</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderPublications = () => (
    <Card>
      <CardHeader>
        <CardTitle>Публикации</CardTitle>
        <CardDescription>Создание публикации и операционные retry/requeue действия.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <Card className="py-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Создать публикацию</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-4 md:grid-cols-4">
              <div className="grid gap-2">
                <Label>Draft ID</Label>
                <Input
                  type="number"
                  min={1}
                  value={pubDraftId || ""}
                  onChange={(event) => setPubDraftId(Number(event.target.value) || 0)}
                />
              </div>
              <div className="grid gap-2">
                <Label>Channel alias</Label>
                <Input
                  type="text"
                  placeholder="main"
                  value={pubChannel}
                  onChange={(event) => setPubChannel(event.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label>Режим</Label>
                <Select value={pubNow ? "now" : "scheduled"} onValueChange={(value) => setPubNow(value === "now")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="now">publish_now=true</SelectItem>
                    <SelectItem value="scheduled">scheduled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>scheduled_at</Label>
                <Input
                  type="datetime-local"
                  value={pubScheduleAt}
                  onChange={(event) => setPubScheduleAt(event.target.value)}
                  disabled={pubNow}
                />
              </div>
            </div>
            <Button type="button" onClick={() => void handleCreatePublication()} disabled={isBusy}>
              Создать публикацию
            </Button>
          </CardContent>
        </Card>

        <Card className="py-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Последние публикации</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>Поиск</Label>
                <Input
                  type="text"
                  placeholder="ID, draft_id, channel, log"
                  value={publicationQuery}
                  onChange={(event) => setPublicationQuery(event.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label>Фильтр по статусу</Label>
                <Select value={publicationStatusFilter} onValueChange={setPublicationStatusFilter}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">all</SelectItem>
                    <SelectItem value="queued">queued</SelectItem>
                    <SelectItem value="running">running</SelectItem>
                    <SelectItem value="scheduled">scheduled</SelectItem>
                    <SelectItem value="success">success</SelectItem>
                    <SelectItem value="error">error</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>draft_id</TableHead>
                  <TableHead>channel</TableHead>
                  <TableHead>status</TableHead>
                  <TableHead>scheduled_at</TableHead>
                  <TableHead>published_at</TableHead>
                  <TableHead>actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPublications.map((publication) => (
                  <TableRow key={publication.id}>
                    <TableCell>{publication.id}</TableCell>
                    <TableCell>{publication.draft_id ?? "-"}</TableCell>
                    <TableCell>{publication.channel_alias || publication.channel_id || "-"}</TableCell>
                    <TableCell>
                      <Badge variant={publication.status === "error" ? "destructive" : "secondary"}>
                        {publication.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{humanizeDate(publication.scheduled_at)}</TableCell>
                    <TableCell>{humanizeDate(publication.published_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            if (!window.confirm(`Повторно отправить publication #${publication.id}?`)) {
                              return;
                            }
                            void handleRetryPublication(publication.id);
                          }}
                          disabled={isBusy}
                        >
                          Retry
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            if (!window.confirm(`Requeue failed publication #${publication.id}?`)) {
                              return;
                            }
                            void handleRequeueFailedPublication(publication.id);
                          }}
                          disabled={isBusy}
                        >
                          Requeue
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </CardContent>
    </Card>
  );

  return (
    <main className="page-container space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            NewsBot Web
            <Badge variant="outline">
              #{initialSession.id} ({initialSession.role})
            </Badge>
          </CardTitle>
          <CardDescription>
            Операционная панель модерации, LLM-задач и публикаций.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Label htmlFor="live-refresh" className="text-sm">
              Live refresh
            </Label>
            <Switch
              id="live-refresh"
              checked={liveRefreshEnabled}
              onCheckedChange={setLiveRefreshEnabled}
            />
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              void refreshDrafts();
              void refreshPublications();
            }}
          >
            <RefreshCw className="size-4" />
            Обновить сейчас
          </Button>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as TabKey)}>
        <TabsList>
          <TabsTrigger value="drafts">Черновики + LLM</TabsTrigger>
          <TabsTrigger value="sources">Источники</TabsTrigger>
          <TabsTrigger value="publications">Публикации</TabsTrigger>
        </TabsList>
        <TabsContent value="drafts" className="mt-4">
          {renderDrafts()}
        </TabsContent>
        <TabsContent value="sources" className="mt-4">
          {renderSources()}
        </TabsContent>
        <TabsContent value="publications" className="mt-4">
          {renderPublications()}
        </TabsContent>
      </Tabs>

      <div className="fixed right-4 bottom-4 z-50 grid gap-2">
        {toasts.map((toast) => (
          <Card
            key={toast.id}
            className={`w-[280px] border py-3 shadow-lg ${
              toast.kind === "success"
                ? "border-green-500/40 bg-green-500/10"
                : toast.kind === "error"
                  ? "border-red-500/40 bg-red-500/10"
                  : "border-blue-500/40 bg-blue-500/10"
            }`}
          >
            <CardContent className="px-4 text-sm">{toast.message}</CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
