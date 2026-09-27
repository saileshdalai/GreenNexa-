"use client";

import React, { createContext, useContext, useEffect, useState, useTransition } from "react";

export type ThemeMode = "day" | "night";
export type ColorTheme = "emerald" | "ocean-blue" | "indigo" | "teal" | "graphite" | "amber";

export interface ColorThemeOption {
  id: ColorTheme;
  label: string;
  swatch: string;
}

export const COLOR_THEMES: ColorThemeOption[] = [
  { id: "emerald", label: "Emerald", swatch: "#10b981" },
  { id: "ocean-blue", label: "Ocean Blue", swatch: "#0284c7" },
  { id: "indigo", label: "Indigo", swatch: "#6366f1" },
  { id: "teal", label: "Teal", swatch: "#14b8a6" },
  { id: "graphite", label: "Graphite", swatch: "#64748b" },
  { id: "amber", label: "Amber", swatch: "#f59e0b" },
];

interface ThemeContextType {
  theme: ThemeMode;
  toggleTheme: () => void;
  setTheme: (theme: ThemeMode) => void;
  isNight: boolean;
  isDay: boolean;
  colorTheme: ColorTheme;
  setColorTheme: (color: ColorTheme) => void;
}

const THEME_STORAGE_KEY = "greennexa_theme";
const COLOR_THEME_STORAGE_KEY = "greennexa_color_theme";
const DEFAULT_THEME: ThemeMode = "day";
const DEFAULT_COLOR_THEME: ColorTheme = "emerald";

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(DEFAULT_THEME);
  const [colorTheme, setColorThemeState] = useState<ColorTheme>(DEFAULT_COLOR_THEME);
  const [, startTransition] = useTransition();

  const applyColorThemeToDOM = (color: ColorTheme) => {
    if (typeof document === "undefined") return;
    document.documentElement.setAttribute("data-color-theme", color);
    if (document.body) {
      document.body.setAttribute("data-color-theme", color);
    }
    window.dispatchEvent(
      new CustomEvent("greennexa_color_theme_changed", {
        detail: { colorTheme: color },
      })
    );
  };

  // Initialize theme from localStorage on client mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === "day" || saved === "night") {
        setThemeState(saved);
        applyThemeToDOM(saved);
      } else {
        setThemeState(DEFAULT_THEME);
        applyThemeToDOM(DEFAULT_THEME);
      }
    } catch {
      applyThemeToDOM(DEFAULT_THEME);
    }

    try {
      const savedColor = localStorage.getItem(COLOR_THEME_STORAGE_KEY) as ColorTheme;
      if (savedColor && COLOR_THEMES.some((t) => t.id === savedColor)) {
        setColorThemeState(savedColor);
        applyColorThemeToDOM(savedColor);
      } else {
        setColorThemeState(DEFAULT_COLOR_THEME);
        applyColorThemeToDOM(DEFAULT_COLOR_THEME);
      }
    } catch {
      applyColorThemeToDOM(DEFAULT_COLOR_THEME);
    }
  }, []);

  const applyThemeToDOM = (mode: ThemeMode) => {
    if (typeof document === "undefined") return;
    document.documentElement.setAttribute("data-theme", mode);
    document.documentElement.classList.remove("theme-day", "theme-night");
    document.documentElement.classList.add(`theme-${mode}`);

    if (document.body) {
      document.body.setAttribute("data-theme", mode);
      document.body.classList.remove("theme-day", "theme-night");
      document.body.classList.add(`theme-${mode}`);
    }

    // Emit custom event for non-React listeners / charts
    window.dispatchEvent(
      new CustomEvent("greennexa_theme_changed", {
        detail: { theme: mode },
      })
    );
  };

  const setTheme = (newTheme: ThemeMode) => {
    if (newTheme !== "day" && newTheme !== "night") return;
    startTransition(() => {
      setThemeState(newTheme);
    });
    try {
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    } catch {}
    applyThemeToDOM(newTheme);
  };

  const setColorTheme = (newColor: ColorTheme) => {
    if (!COLOR_THEMES.some((t) => t.id === newColor)) return;
    startTransition(() => {
      setColorThemeState(newColor);
    });
    try {
      localStorage.setItem(COLOR_THEME_STORAGE_KEY, newColor);
    } catch {}
    applyColorThemeToDOM(newColor);
  };

  const toggleTheme = () => {
    const nextTheme: ThemeMode = theme === "night" ? "day" : "night";
    setTheme(nextTheme);
  };

  return (
    <ThemeContext.Provider
      value={{
        theme,
        toggleTheme,
        setTheme,
        isNight: theme === "night",
        isDay: theme === "day",
        colorTheme,
        setColorTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
