"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { isLoggedIn } from "@/lib/auth";

export default function LocaleRootPage() {
  const router = useRouter();

  useEffect(() => {
    if (isLoggedIn()) {
      router.replace("/dashboard");
    } else {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
    </div>
  );
}
