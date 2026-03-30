"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    onTelegramAuth?: (user: Record<string, unknown>) => void;
  }
}

type Props = {
  botUsername: string;
  onAuth: (payload: Record<string, unknown>) => Promise<void> | void;
};

export default function TelegramWidget({ botUsername, onAuth }: Props) {
  useEffect(() => {
    if (!botUsername) {
      return;
    }

    const scriptId = "telegram-login-widget-script";

    window.onTelegramAuth = async (user: Record<string, unknown>) => {
      await onAuth(user);
    };

    const existing = document.getElementById(scriptId);
    if (existing) {
      return;
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.async = true;
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "8");
    script.setAttribute("data-request-access", "write");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");

    const mount = document.getElementById("telegram-login-widget-mount");
    if (mount) {
      mount.innerHTML = "";
      mount.appendChild(script);
    }

    return () => {
      window.onTelegramAuth = undefined;
    };
  }, [botUsername, onAuth]);

  return <div id="telegram-login-widget-mount" />;
}

