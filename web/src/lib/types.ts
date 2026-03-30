export type DraftStatus = "new" | "flagged" | "approved" | "rejected" | "published";

export type DraftOut = {
  id: number;
  article_raw_id: number | null;
  target_language: string;
  title_original: string | null;
  content_original: string | null;
  title_translated: string | null;
  content_translated: string | null;
  source_language: string | null;
  flags: Array<Record<string, unknown>> | null;
  status: DraftStatus;
};

export type SourceOut = {
  id: number;
  name: string;
  type: "rss" | "site";
  url: string;
  enabled: boolean;
  schedule_cron: string | null;
  translate_enabled: boolean;
  default_target_language: string;
  extraction_rules: Record<string, unknown> | null;
};
