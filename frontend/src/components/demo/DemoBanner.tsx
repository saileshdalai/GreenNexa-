"use client";

import React from "react";
import { useDemo } from "@/context/DemoContext";

export const DemoBanner: React.FC = () => {
  const { demoModeActive, activeDemoModules, toggleDemoMode } = useDemo();

  if (!demoModeActive) return null;

  const moduleLabel = activeDemoModules && activeDemoModules.length > 0
    ? ` (${activeDemoModules.map((m) => m.toUpperCase()).join(", ")})`
    : "";

  return (
    <div
      style={{
        backgroundColor: "rgba(16, 185, 129, 0.12)",
        borderBottom: "1px solid rgba(16, 185, 129, 0.25)",
        color: "#10b981",
        padding: "8px 16px",
        fontSize: "0.85rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "8px",
        fontWeight: 500,
        boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
        <span
          style={{
            display: "inline-block",
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            backgroundColor: "#10b981",
            boxShadow: "0 0 8px #10b981",
            flexShrink: 0,
          }}
        />
        <span style={{ fontSize: "12px", lineHeight: 1.4 }}>
          <strong>Demo Mode Active{moduleLabel}</strong> — only active module data simulates; other modules remain unchanged.
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginLeft: "auto" }}>
        <span style={{ fontSize: "0.75rem", opacity: 0.85, background: "rgba(16, 185, 129, 0.2)", padding: "2px 8px", borderRadius: "12px", whiteSpace: "nowrap" }}>
          Module Scoped
        </span>
        <button
          onClick={() => toggleDemoMode()}
          style={{
            background: "transparent",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            color: "#10b981",
            fontSize: "0.75rem",
            padding: "2px 8px",
            borderRadius: "4px",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Exit Demo Mode
        </button>
      </div>
    </div>
  );
};
