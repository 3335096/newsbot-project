"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
    <main className="page-container">
      <div className="mx-auto grid max-w-3xl gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Вход в веб-панель</CardTitle>
            <CardDescription>
              Вход доступен через <b>Telegram WebApp initData</b> (внутри бота) и{" "}
              <b>Telegram Login Widget</b> (в браузере).
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Card className="py-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Быстрый вход из Telegram</CardTitle>
                <CardDescription>
                  Если страница открыта как Mini App, нажмите кнопку — вход выполнится автоматически.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button type="button" onClick={fillFromTelegramWebApp} disabled={isPending}>
                  {isPending ? "Проверяем..." : "Войти через Telegram WebApp"}
                </Button>
                <p className="text-sm text-muted-foreground">
                  <a href={TELEGRAM_WEBAPP_DOCS_URL} target="_blank" rel="noreferrer">
                    Документация Telegram WebApp initData
                  </a>
                </p>
              </CardContent>
            </Card>

            <Card className="py-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Вход через Telegram Login Widget</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {botUsername ? (
                  <TelegramWidget botUsername={botUsername} onAuth={onWidgetAuth} />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Укажите `TELEGRAM_BOT_USERNAME` в окружении, чтобы включить login widget.
                  </p>
                )}
                <p className="text-sm text-muted-foreground">
                  <a href={TELEGRAM_LOGIN_DOCS_URL} target="_blank" rel="noreferrer">
                    Telegram docs
                  </a>
                </p>
              </CardContent>
            </Card>

            <details>
              <summary className="cursor-pointer text-sm font-medium">Ручной fallback (debug)</summary>
              <form className="mt-3 grid gap-3" onSubmit={onSubmit}>
                <div className="grid gap-2">
                  <Label htmlFor="mode">Режим входа</Label>
                  <Select value={mode} onValueChange={(value) => setMode(value as AuthMode)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="telegram_init_data">Telegram WebApp initData</SelectItem>
                      <SelectItem value="telegram_login_widget">Telegram Login Widget JSON</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="payload">
                    {mode === "telegram_init_data" ? "initData string" : "Widget JSON payload"}
                  </Label>
                  <Input
                    id="payload"
                    value={payload}
                    onChange={(event) => setPayload(event.target.value)}
                    placeholder={placeholder}
                    required
                  />
                </div>
                <Button type="submit" disabled={isPending}>
                  {isPending ? "Входим..." : "Войти вручную"}
                </Button>
              </form>
            </details>
            {error ? <p className="text-sm font-medium text-destructive">{error}</p> : null}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
