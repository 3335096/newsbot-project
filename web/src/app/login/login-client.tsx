"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import TelegramWidget from "./telegram-widget";

type AuthMode = "telegram_init_data" | "telegram_login_widget";

const TELEGRAM_LOGIN_DOCS_URL =
  "https://core.telegram.org/widgets/login#checking-authorization";
const TELEGRAM_WEBAPP_DOCS_URL = "https://core.telegram.org/bots/webapps#initializing-mini-apps";

type Props = {
  botUsername: string;
};

export default function LoginClient({ botUsername }: Props) {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("telegram_init_data");
  const [payload, setPayload] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);
  const autoAuthTriggeredRef = useRef(false);

  const placeholder = useMemo(() => {
    if (mode === "telegram_init_data") {
      return "query_id=...&user=%7B...%7D&auth_date=...&hash=...";
    }
    return JSON.stringify(
      {
        id: 12345678,
        first_name: "John",
        username: "john_doe",
        auth_date: 1700000000,
        hash: "telegram_hash",
      },
      null,
      2,
    );
  }, [mode]);

  const submitAuth = useCallback(
    async (authMode: AuthMode, authPayload: string) => {
      setError(null);
      setIsPending(true);
      try {
        const response = await fetch("/api/auth/telegram", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            payload: authPayload,
            mode: authMode,
          }),
        });

        if (!response.ok) {
          const data = (await response.json().catch(() => ({}))) as Record<string, unknown>;
          const detail = String(data.detail ?? data.error ?? "Не удалось авторизоваться");
          throw new Error(detail);
        }
        router.push("/dashboard");
        router.refresh();
      } catch (submitError) {
        const message = submitError instanceof Error ? submitError.message : "Ошибка авторизации";
        setError(message);
      } finally {
        setIsPending(false);
      }
    },
    [router],
  );

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await submitAuth(mode, payload);
  };

  const fillFromTelegramWebApp = async () => {
    try {
      const maybeTelegram = (
        window as Window & {
          Telegram?: { WebApp?: { initData?: string } };
        }
      ).Telegram;
      const initData = maybeTelegram?.WebApp?.initData || "";
      if (!initData) {
        setError("Telegram WebApp initData не найден. Откройте страницу из бота.");
        return;
      }
      setMode("telegram_init_data");
      setPayload(initData);
      setError(null);
      await submitAuth("telegram_init_data", initData);
    } catch {
      setError("Не удалось прочитать initData из Telegram WebApp");
    }
  };

  const onWidgetAuth = async (widgetPayload: Record<string, unknown>) => {
    await submitAuth("telegram_login_widget", JSON.stringify(widgetPayload));
  };

  useEffect(() => {
    if (autoAuthTriggeredRef.current) {
      return;
    }
    const maybeTelegram = (
      window as Window & {
        Telegram?: { WebApp?: { initData?: string } };
      }
    ).Telegram;
    const initData = maybeTelegram?.WebApp?.initData || "";
    if (!initData) {
      return;
    }
    autoAuthTriggeredRef.current = true;
    void submitAuth("telegram_init_data", initData);
  }, [submitAuth]);

  return (
    <main className="container">
      <section className="card">
        <h1>Вход в веб-панель</h1>
        <p>
          Вход доступен через <b>Telegram WebApp initData</b> (внутри бота) и{" "}
          <b>Telegram Login Widget</b> (в браузере).
        </p>
        <div className="card">
          <h2>Быстрый вход из Telegram</h2>
          <p className="hint">
            Если страница открыта как Mini App, нажмите кнопку — вход выполнится автоматически.
          </p>
          <button type="button" onClick={fillFromTelegramWebApp} disabled={isPending}>
            {isPending ? "Проверяем..." : "Войти через Telegram WebApp"}
          </button>
          <p className="hint">
            <a href={TELEGRAM_WEBAPP_DOCS_URL} target="_blank" rel="noreferrer">
              Документация Telegram WebApp initData
            </a>
          </p>
        </div>

        <div className="card">
          <h2>Вход через Telegram Login Widget</h2>
          {botUsername ? (
            <TelegramWidget botUsername={botUsername} onAuth={onWidgetAuth} />
          ) : (
            <p className="hint">
              Укажите `TELEGRAM_BOT_USERNAME` в окружении, чтобы включить login widget.
            </p>
          )}
          <p className="hint">
            <a href={TELEGRAM_LOGIN_DOCS_URL} target="_blank" rel="noreferrer">
              Telegram docs
            </a>
          </p>
        </div>

        <details>
          <summary>Ручной fallback (debug)</summary>
          <form onSubmit={onSubmit}>
            <label htmlFor="mode">Режим входа</label>
            <select
              id="mode"
              value={mode}
              onChange={(event) => setMode(event.target.value as AuthMode)}
            >
              <option value="telegram_init_data">Telegram WebApp initData</option>
              <option value="telegram_login_widget">Telegram Login Widget JSON</option>
            </select>

            <label htmlFor="payload">
              {mode === "telegram_init_data" ? "initData string" : "Widget JSON payload"}
            </label>
            <textarea
              id="payload"
              value={payload}
              onChange={(event) => setPayload(event.target.value)}
              placeholder={placeholder}
              required
            />
            <button type="submit" disabled={isPending}>
              {isPending ? "Входим..." : "Войти вручную"}
            </button>
          </form>
        </details>
        {error ? <p className="error">{error}</p> : null}
      </section>
    </main>
  );
}
