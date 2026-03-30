import { env } from "@/lib/env";
import LoginClient from "./login-client";

export default function LoginPage() {
  return <LoginClient botUsername={env.botUsername} />;
}
