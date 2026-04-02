import Link from "next/link";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  const confirmText = String(formData.get("confirm_delete") ?? "").trim().toLowerCase();
  if (!sourceId) {
    throw new Error("source_id is required");
  }
  if (confirmText !== "delete") {
    throw new Error("Type DELETE to confirm removal");
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
    <main className="page-container space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Источники</CardTitle>
              <CardDescription>Управление источниками и ручной parse-now.</CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline" size="sm">
                <Link href="/dashboard">Назад к панели</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/dashboard/publications">Публикации</Link>
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {session.role === "admin" ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Добавить источник</CardTitle>
            <CardDescription>
              Новые источники используются scheduler-ом и ручным parse-now.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form action={createSource} className="grid gap-4">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <div className="grid gap-2">
                  <Label htmlFor="create-name">Название</Label>
                  <Input id="create-name" name="name" type="text" required />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="create-type">Тип</Label>
                  <Select name="type" defaultValue="rss">
                    <SelectTrigger id="create-type">
                      <SelectValue placeholder="Выберите тип" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="rss">rss</SelectItem>
                      <SelectItem value="site">site</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="create-url">URL</Label>
                  <Input id="create-url" name="url" type="url" required />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="create-cron">Cron</Label>
                  <Input id="create-cron" name="schedule_cron" type="text" placeholder="*/30 * * * *" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="create-lang">Язык по умолчанию</Label>
                  <Input id="create-lang" name="default_target_language" type="text" defaultValue="ru" />
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    name="enabled"
                    type="checkbox"
                    defaultChecked
                    className="size-4 rounded border border-input"
                  />
                  enabled
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    name="translate_enabled"
                    type="checkbox"
                    defaultChecked
                    className="size-4 rounded border border-input"
                  />
                  translate_enabled
                </label>
              </div>
              <div>
                <Button type="submit">Создать</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Список источников</CardTitle>
          <CardDescription>Всего: {sources.length}</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Название</TableHead>
                <TableHead>Тип</TableHead>
                <TableHead>URL</TableHead>
                <TableHead>Включен</TableHead>
                <TableHead>Перевод</TableHead>
                <TableHead>Cron</TableHead>
                <TableHead>Язык</TableHead>
                <TableHead>Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sources.map((source) => (
                <TableRow key={source.id}>
                  <TableCell>{source.id}</TableCell>
                  <TableCell>{source.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{source.type}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[260px]">
                    <a href={source.url} target="_blank" rel="noreferrer" className="truncate">
                      {source.url}
                    </a>
                  </TableCell>
                  <TableCell>{source.enabled ? "yes" : "no"}</TableCell>
                  <TableCell>{source.translate_enabled ? "yes" : "no"}</TableCell>
                  <TableCell>{source.schedule_cron || "-"}</TableCell>
                  <TableCell>{source.default_target_language}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      <form action={parseNow}>
                        <input type="hidden" name="source_id" value={source.id} />
                        <Button type="submit" size="sm" variant="outline">
                          Parse now
                        </Button>
                      </form>
                    </div>
                    {session.role === "admin" ? (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-sm text-muted-foreground">Edit / Delete</summary>
                        <div className="mt-2 grid gap-3 rounded-md border p-3">
                          <form action={updateSource} className="grid gap-2">
                            <input type="hidden" name="source_id" value={source.id} />
                            <Label>Название</Label>
                            <Input name="name" type="text" defaultValue={source.name} required />
                            <Label>Cron</Label>
                            <Input name="schedule_cron" type="text" defaultValue={source.schedule_cron || ""} />
                            <Label>Язык</Label>
                            <Input
                              name="default_target_language"
                              type="text"
                              defaultValue={source.default_target_language}
                            />
                            <div className="flex flex-wrap items-center gap-4">
                              <label className="flex items-center gap-2 text-sm">
                                <input
                                  name="enabled"
                                  type="checkbox"
                                  defaultChecked={source.enabled}
                                  className="size-4 rounded border border-input"
                                />
                                enabled
                              </label>
                              <label className="flex items-center gap-2 text-sm">
                                <input
                                  name="translate_enabled"
                                  type="checkbox"
                                  defaultChecked={source.translate_enabled}
                                  className="size-4 rounded border border-input"
                                />
                                translate_enabled
                              </label>
                            </div>
                            <Button type="submit" size="sm">
                              Сохранить
                            </Button>
                          </form>
                          <form action={deleteSource} className="grid gap-2">
                            <input type="hidden" name="source_id" value={source.id} />
                            <Label>Подтвердите удаление</Label>
                            <Input name="confirm_delete" type="text" placeholder="DELETE" required />
                            <Button type="submit" size="sm" variant="destructive">
                              Удалить
                            </Button>
                          </form>
                        </div>
                      </details>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </main>
  );
}
