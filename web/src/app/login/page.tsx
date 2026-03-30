"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type AuthMode = "telegram_init_data" | "telegram_login_widget";

const TELEGRAM_LOGIN_DOCS_URL =
  "https://core.telegram.org/widgets/login#checking-authorization";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("telegram_init_data");
  const [payload, setPayload] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

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

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsPending(true);
    try {
      const response = await fetch("/api/auth/telegram", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          payload,
          mode,
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
      const message =
        submitError instanceof Error ? submitError.message : "Ошибка авторизации";
      setError(message);
    } finally {
      setIsPending(false);
    }
  };

  const fillFromTelegramWebApp = () => {
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
    } catch {
      setError("Не удалось прочитать initData из Telegram WebApp");
    }
  };

  return (
    <main className="container">
      <section className="card">
        <h1>Вход в веб-панель</h1>
        <p>
          Поддерживаются два режима: <b>Telegram WebApp initData</b> (если вы открыли панель из
          бота) и <b>Telegram Login Widget</b> (если входите из браузера).
        </p>
        <div className="actions">
          <button type="button" onClick={fillFromTelegramWebApp}>
            Взять initData из Telegram WebApp
          </button>
        </div>
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
          <p className="hint">
            В production payload автоматически подставляется Telegram-клиентом, форма оставлена
            как удобный fallback для запуска и отладки.
          </p>
          {error ? <p className="error">{error}</p> : null}
          <button type="submit" disabled={isPending}>
            {isPending ? "Входим..." : "Войти"}
          </button>
        </form>
        <p className="hint">
          Как проверить подпись Login Widget:{" "}
          <a href={TELEGRAM_LOGIN_DOCS_URL} target="_blank" rel="noreferrer">
            Telegram docs
          </a>
        </p>
      </section>
    </main>
  );
}
