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

const allowedRaw = process.env.TELEGRAM_ALLOWED_USER_IDS || process.env.TELEGRAM_ADMIN_IDS || "";

export const env = {
  botToken: readRequired("TELEGRAM_BOT_TOKEN"),
  webAuthSecret: readRequired("WEB_AUTH_SECRET"),
  backendBaseUrl: readRequired("WEB_BACKEND_BASE_URL").replace(/\/+$/, ""),
  cookieName: (process.env.WEB_SESSION_COOKIE_NAME || "newsbot_web_session").trim(),
  sessionTtlSeconds: Number(process.env.WEB_SESSION_TTL_SECONDS || "86400"),
  allowedUserIds: parseIdSet(allowedRaw),
  adminUserIds: parseIdSet(process.env.TELEGRAM_ADMIN_IDS),
};
