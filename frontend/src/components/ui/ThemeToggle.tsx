"use client";

import React from "react";
import { useTheme } from "@/context/ThemeContext";

interface ThemeToggleProps {
  variant?: "segmented" | "compact";
  className?: string;
  style?: React.CSSProperties;
}

export function ThemeToggle({ variant = "segmented", className = "", style = {} }: ThemeToggleProps) {
  const { theme, setTheme, isNight, isDay } = useTheme();

  if (variant === "compact") {
    return (
      <button
        type="button"
        onClick={() => setTheme(isNight ? "day" : "night")}
        aria-label={isNight ? "Current theme: Night Mode. Switch to Day Mode" : "Current theme: Day Mode. Switch to Night Mode"}
        title={isNight ? "Switch to Day Mode ☀️" : "Switch to Night Mode 🌙"}
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "6px",
          padding: "6px 10px",
          borderRadius: "8px",
          background: "var(--clr-surface-2)",
          border: "1px solid var(--clr-border)",
          color: "var(--clr-text-primary)",
          fontSize: "12px",
          fontWeight: 600,
          cursor: "pointer",
          transition: "all 0.2s ease",
          outline: "none",
          ...style,
        }}
        className={className}
      >
        <span style={{ fontSize: "14px", lineHeight: 1 }} aria-hidden="true">
          {isNight ? "🌙" : "☀️"}
        </span>
        <span>{isNight ? "Night" : "Day"}</span>
      </button>
    );
  }

  return (
    <div
      role="radiogroup"
      aria-label="Application appearance theme: Day Mode or Night Mode"
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "3px",
        borderRadius: "24px",
        backgroundColor: "var(--clr-surface-2)",
        border: "1px solid var(--clr-border)",
        boxShadow: "inset 0 1px 2px rgba(0, 0, 0, 0.08)",
        fontSize: "12px",
        fontWeight: 600,
        gap: "2px",
        userSelect: "none",
        ...style,
      }}
      className={className}
    >
      {/* ☀️ Day Mode Option */}
      <button
        type="button"
        role="radio"
        aria-checked={isDay}
        aria-label="Day Mode (Light Appearance)"
        title="Switch to Day Mode ☀️"
        onClick={() => setTheme("day")}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "5px",
          padding: "4px 10px",
          borderRadius: "18px",
          backgroundColor: isDay ? "var(--clr-surface)" : "transparent",
          color: isDay ? "var(--clr-text-primary)" : "var(--clr-text-muted)",
          border: isDay ? "1px solid var(--clr-border)" : "1px solid transparent",
          boxShadow: isDay ? "0 2px 5px rgba(0, 0, 0, 0.12)" : "none",
          cursor: "pointer",
          transition: "all 0.18s ease-in-out",
          outline: "none",
          fontWeight: isDay ? 700 : 500,
        }}
      >
        <span style={{ fontSize: "13px", lineHeight: 1 }} aria-hidden="true">
          ☀️
        </span>
        <span>Day</span>
      </button>

      {/* 🌙 Night Mode Option */}
      <button
        type="button"
        role="radio"
        aria-checked={isNight}
        aria-label="Night Mode (Dark Appearance)"
        title="Switch to Night Mode 🌙"
        onClick={() => setTheme("night")}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "5px",
          padding: "4px 10px",
          borderRadius: "18px",
          backgroundColor: isNight ? "var(--clr-surface)" : "transparent",
          color: isNight ? "var(--clr-text-primary)" : "var(--clr-text-muted)",
          border: isNight ? "1px solid var(--clr-border)" : "1px solid transparent",
          boxShadow: isNight ? "0 2px 5px rgba(0, 0, 0, 0.25)" : "none",
          cursor: "pointer",
          transition: "all 0.18s ease-in-out",
          outline: "none",
          fontWeight: isNight ? 700 : 500,
        }}
      >
        <span style={{ fontSize: "13px", lineHeight: 1 }} aria-hidden="true">
          🌙
        </span>
        <span>Night</span>
      </button>
    </div>
  );
}
