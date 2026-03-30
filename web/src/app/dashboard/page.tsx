import { redirect } from "next/navigation";

import ClientDashboard from "@/app/dashboard/client-dashboard";
import { env } from "@/lib/env";
import { getSessionUser } from "@/lib/session";
import type { DraftOut, PublicationOut } from "@/lib/types";

async function fetchDrafts(): Promise<DraftOut[]> {
  const response = await fetch(`${env.backendBaseUrl}/api/drafts`, { cache: "no-store" });
  if (!response.ok) {
    return [];
  }
  return (await response.json()) as DraftOut[];
}

async function fetchPublications(): Promise<PublicationOut[]> {
  const response = await fetch(`${env.backendBaseUrl}/api/publications?limit=100`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return [];
  }
  return (await response.json()) as PublicationOut[];
}

export default async function DashboardPage() {
  const session = await getSessionUser();
  if (!session) {
    redirect("/login");
  }
  const [drafts, publications] = await Promise.all([fetchDrafts(), fetchPublications()]);
  return (
    <ClientDashboard
      initialSession={session}
      initialDrafts={drafts}
      initialPublications={publications}
    />
  );
}
