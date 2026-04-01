import { redirect } from "next/navigation";

import { env } from "@/lib/env";
import LoginClient from "./login-client";

export default function LoginPage() {
  if (env.disableTelegramAuth) {
    redirect("/dashboard");
  }
  return <LoginClient botUsername={env.botUsername} />;
}
