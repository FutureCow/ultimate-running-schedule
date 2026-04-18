"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "dark" | "light" | "system";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (t: Theme) => void;
  resolved: "dark" | "light";
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  setTheme: () => {},
  resolved: "dark",
});

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [resolved, setResolved] = useState<"dark" | "light">("dark");

  // Resolve system preference
  function resolveTheme(t: Theme): "dark" | "light" {
    if (t === "system") {
      return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }
    return t;
  }

  function applyTheme(resolved: "dark" | "light") {
    if (resolved === "light") {
      document.documentElement.classList.add("light");
    } else {
      document.documentElement.classList.remove("light");
    }
  }

  function setTheme(t: Theme) {
    localStorage.setItem("theme", t);
    setThemeState(t);
    const r = resolveTheme(t);
    setResolved(r);
    applyTheme(r);
  }

  useEffect(() => {
    const stored = (localStorage.getItem("theme") as Theme) || "dark";
    setThemeState(stored);
    const r = resolveTheme(stored);
    setResolved(r);
    applyTheme(r);

    // Watch system preference changes when in system mode
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    function onSystemChange() {
      const current = (localStorage.getItem("theme") as Theme) || "dark";
      if (current === "system") {
        const r = resolveTheme("system");
        setResolved(r);
        applyTheme(r);
      }
    }
    mq.addEventListener("change", onSystemChange);
    return () => mq.removeEventListener("change", onSystemChange);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolved }}>
      {children}
    </ThemeContext.Provider>
  );
}
