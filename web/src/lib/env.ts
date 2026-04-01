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

function parseBooleanEnv(raw: string | undefined): boolean {
  const normalized = (raw || "")
    .trim()
    .replace(/^['"]+|['"]+$/g, "")
    .toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
}

function normalizeUrlEnv(raw: string | undefined): string {
  const normalized = (raw || "").trim().replace(/^['"]+|['"]+$/g, "").replace(/\/+$/, "");
  if (!normalized) {
    return "";
  }
  if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
    return normalized;
  }
  return `https://${normalized}`;
}

export const env = {
  get botToken(): string {
    return readRequired("TELEGRAM_BOT_TOKEN");
  },
  get webAuthSecret(): string {
    return readRequired("WEB_AUTH_SECRET");
  },
  get backendBaseUrl(): string {
    return normalizeUrlEnv(readRequired("WEB_BACKEND_BASE_URL"));
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
    return normalizeUrlEnv(process.env.WEB_APP_URL);
  },
  get botUsername(): string {
    return (process.env.TELEGRAM_BOT_USERNAME || "").trim().replace(/^@+/, "");
  },
  get disableTelegramAuth(): boolean {
    return parseBooleanEnv(process.env.WEB_DISABLE_TELEGRAM_AUTH);
  },
  get mvpRole(): "admin" | "editor" {
    return (process.env.WEB_MVP_ROLE || "").trim().toLowerCase() === "editor" ? "editor" : "admin";
  },
};
