"use client";

import { useEffect, useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { isLoggedIn } from "@/lib/auth";

/**
 * Keeps signed-out visitors out of the app pages.
 *
 * The API already refuses every request without a token, but the pages
 * themselves rendered anyway: a visitor could open the dashboard and fill in
 * the whole plan form before hitting an error. Nothing renders until the token
 * check has run, so there is no flash of an empty app either.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    if (isLoggedIn()) setAllowed(true);
    else router.replace("/login");
  }, [router]);

  return allowed ? <>{children}</> : null;
}
