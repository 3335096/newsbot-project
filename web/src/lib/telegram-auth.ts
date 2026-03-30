import crypto from "node:crypto";

function parseInitDataRaw(initDataRaw: string): Record<string, string> {
  const params = new URLSearchParams(initDataRaw);
  const parsed: Record<string, string> = {};
  params.forEach((value, key) => {
    parsed[key] = value;
  });
  return parsed;
}

function buildDataCheckString(payload: Record<string, string>): string {
  const entries = Object.entries(payload)
    .filter(([key]) => key !== "hash")
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`);
  return entries.join("\n");
}

function timingSafeEqualHex(a: string, b: string): boolean {
  if (!a || !b || a.length !== b.length) {
    return false;
  }
  return crypto.timingSafeEqual(Buffer.from(a, "hex"), Buffer.from(b, "hex"));
}

export type TelegramAuthUser = {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date?: number;
};

export type VerifiedTelegramAuth = {
  user: TelegramAuthUser;
  authDate: number;
};

function parseAuthDate(value: string | undefined): number | null {
  if (!value) {
    return null;
  }
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) {
    return null;
  }
  return Math.floor(n);
}

export function verifyTelegramAuthPayload(
  payloadRaw: Record<string, string>,
  botToken: string,
  maxAgeSeconds: number,
): VerifiedTelegramAuth | null {
  const hash = payloadRaw.hash;
  const userRaw = payloadRaw.user;
  if (!hash || !userRaw) {
    return null;
  }

  const dataCheckString = buildDataCheckString(payloadRaw);
  const secret = crypto.createHash("sha256").update(botToken).digest();
  const digest = crypto
    .createHmac("sha256", secret)
    .update(dataCheckString)
    .digest("hex");

  if (!timingSafeEqualHex(digest, hash)) {
    return null;
  }

  const authDate = parseAuthDate(payloadRaw.auth_date);
  if (!authDate) {
    return null;
  }
  if (Math.floor(Date.now() / 1000) - authDate > maxAgeSeconds) {
    return null;
  }

  let user: TelegramAuthUser;
  try {
    user = JSON.parse(userRaw) as TelegramAuthUser;
  } catch {
    return null;
  }

  if (!user?.id || !Number.isFinite(user.id)) {
    return null;
  }

  return { user: { ...user, auth_date: authDate }, authDate };
}

export function verifyTelegramInitData(
  initDataRaw: string,
  botToken: string,
  maxAgeSeconds: number,
): VerifiedTelegramAuth | null {
  const payload = parseInitDataRaw(initDataRaw);
  return verifyTelegramAuthPayload(payload, botToken, maxAgeSeconds);
}
