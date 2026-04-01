const REQUIRED_KEYS = ["TELEGRAM_BOT_TOKEN", "WEB_AUTH_SECRET", "WEB_BACKEND_BASE_URL"] as const;
type RequiredKey = (typeof REQUIRED_KEYS)[number];

function readRequired(key: RequiredKey): string {
  const value = process.env[key]?.trim();
  if (!value) {
    throw new Error(`Missing required env var: ${key}`);
  }
  return value;
}

function parseIdSet(raw: string | undefined): Set<number> {
  return new Set(
    (raw || "")
      .split(",")
      .map((entry) => Number(entry.trim()))
      .filter((entry) => Number.isInteger(entry)),
  );
}

export const env = {
  get botToken(): string {
    return readRequired("TELEGRAM_BOT_TOKEN");
  },
  get webAuthSecret(): string {
    return readRequired("WEB_AUTH_SECRET");
  },
  get backendBaseUrl(): string {
    return readRequired("WEB_BACKEND_BASE_URL").replace(/\/+$/, "");
  },
  get cookieName(): string {
    return (process.env.WEB_SESSION_COOKIE_NAME || "newsbot_web_session").trim();
  },
  get sessionTtlSeconds(): number {
    return Number(process.env.WEB_SESSION_TTL_SECONDS || "86400");
  },
  get allowedUserIds(): Set<number> {
    return parseIdSet(process.env.TELEGRAM_ALLOWED_USER_IDS || process.env.TELEGRAM_ADMIN_IDS || "");
  },
  get adminUserIds(): Set<number> {
    return parseIdSet(process.env.TELEGRAM_ADMIN_IDS);
  },
  get publicWebUrl(): string {
    return (process.env.WEB_APP_URL || "").trim().replace(/\/+$/, "");
  },
  get botUsername(): string {
    return (process.env.TELEGRAM_BOT_USERNAME || "").trim().replace(/^@+/, "");
  },
  get disableTelegramAuth(): boolean {
    const raw = (process.env.WEB_DISABLE_TELEGRAM_AUTH || "").trim().toLowerCase();
    return raw === "1" || raw === "true" || raw === "yes" || raw === "on";
  },
  get mvpRole(): "admin" | "editor" {
    return (process.env.WEB_MVP_ROLE || "").trim().toLowerCase() === "editor" ? "editor" : "admin";
  },
};
