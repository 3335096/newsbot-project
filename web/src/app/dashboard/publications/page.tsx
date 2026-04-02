import Link from "next/link";
import { redirect } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
    <main className="page-container space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Публикации</CardTitle>
              <CardDescription>Сводный список публикаций (последние 200).</CardDescription>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard">Назад к панели</Link>
            </Button>
          </div>
        </CardHeader>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>draft_id</TableHead>
                <TableHead>channel</TableHead>
                <TableHead>status</TableHead>
                <TableHead>scheduled_at</TableHead>
                <TableHead>published_at</TableHead>
                <TableHead>log</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {publications.map((publication) => (
                <TableRow key={publication.id}>
                  <TableCell>{publication.id}</TableCell>
                  <TableCell>{publication.draft_id ?? "-"}</TableCell>
                  <TableCell>{publication.channel_alias || publication.channel_id || "-"}</TableCell>
                  <TableCell>
                    <Badge variant={publication.status === "error" ? "destructive" : "secondary"}>
                      {publication.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{publication.scheduled_at || "-"}</TableCell>
                  <TableCell>{publication.published_at || "-"}</TableCell>
                  <TableCell className="max-w-[320px] whitespace-normal">{publication.log || "-"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </main>
  );
}
