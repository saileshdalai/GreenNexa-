"use client";

/**
 * GreenNexa — Dashboard Style compact submenu.
 *
 * Renders the four presentation styles:
 * 1. Executive
 * 2. Operations
 * 3. Analytics
 * 4. Command Center
 *
 * Designed as a compact, nested submenu inside the "..." dashboard menu.
 * Persists the selection through DashboardStyleContext (presentation only).
 */

import React, { useState } from "react";
import { Check, ChevronDown, LayoutDashboard } from "lucide-react";
import { useDashboardStyle } from "@/context/DashboardStyleContext";
import { DashboardStyleDefinition } from "@/lib/dashboardStyles";

const TONE_COLORS: Record<DashboardStyleDefinition["preview"]["cells"][number]["tone"], string> = {
  surface: "rgba(148,163,184,0.35)",
  accent: "var(--clr-primary)",
  alert: "rgba(239,68,68,0.7)",
  muted: "rgba(148,163,184,0.18)",
};

function StylePreview({ definition }: { definition: DashboardStyleDefinition }) {
  return (
    <span
      aria-hidden="true"
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${definition.preview.columns}, 1fr)`,
        gap: "2px",
        width: "36px",
        height: "26px",
        padding: "2px",
        borderRadius: "4px",
        background: "var(--clr-surface-2)",
        border: "1px solid var(--clr-border)",
        flexShrink: 0,
      }}
    >
      {definition.preview.cells.map((cell, i) => (
        <span
          key={i}
          style={{
            gridColumn: `span ${cell.span}`,
            background: TONE_COLORS[cell.tone],
            borderRadius: "1.5px",
          }}
        />
      ))}
    </span>
  );
}

export function DashboardStyleMenu({ onSelected }: { onSelected?: (style: string) => void }) {
  const { style, styles, saving, error, setStyle } = useDashboardStyle();
  const [isOpen, setIsOpen] = useState(false);

  const activeDef = styles.find((s) => s.id === style) || styles[0];

  return (
    <div style={{ borderBottom: "1px solid var(--clr-border)", paddingBottom: "4px", marginBottom: "4px" }}>
      <button
        type="button"
        role="menuitem"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen((prev) => !prev);
        }}
        aria-expanded={isOpen}
        id="header-menu-dashboard-style"
        title="Choose Dashboard Style"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          width: "100%",
          padding: "8px 12px",
          borderRadius: "8px",
          fontSize: "13px",
          fontWeight: 500,
          color: "var(--clr-text-primary)",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
          outline: "none",
          userSelect: "none",
          whiteSpace: "nowrap",
          transition: "background 0.15s ease, color 0.15s ease",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: "9px" }}>
          <LayoutDashboard size={15} style={{ color: "var(--clr-primary)", flexShrink: 0 }} />
          <span style={{ fontSize: "13px", fontWeight: 500 }}>Dashboard Style</span>
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              padding: "2px 7px",
              borderRadius: "999px",
              fontSize: "11px",
              fontWeight: 700,
              background: "var(--clr-primary-light)",
              color: "var(--clr-primary)",
            }}
          >
            {activeDef?.label || "Executive"}
          </span>
          <ChevronDown
            size={13}
            style={{
              transform: isOpen ? "rotate(180deg)" : "none",
              transition: "transform 0.15s ease",
              color: "var(--clr-text-muted)",
            }}
          />
        </div>
      </button>

      {isOpen && (
        <div
          role="group"
          aria-label="Dashboard Style Options"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "2px",
            padding: "4px 6px",
            background: "var(--clr-surface-2)",
            borderRadius: "8px",
            margin: "2px 0 4px 10px",
            borderLeft: "2px solid var(--clr-primary)",
          }}
        >
          {styles.map((definition) => {
            const active = definition.id === style;
            return (
              <button
                key={definition.id}
                type="button"
                role="menuitemradio"
                aria-checked={active}
                data-dashboard-style-option={definition.id}
                onClick={(e) => {
                  e.stopPropagation();
                  void setStyle(definition.id);
                  onSelected?.(definition.id);
                }}
                title={definition.description}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  width: "100%",
                  padding: "7px 10px",
                  background: active ? "var(--clr-primary-light)" : "transparent",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  textAlign: "left",
                  fontFamily: "inherit",
                  transition: "all 0.15s ease",
                }}
              >
                <StylePreview definition={definition} />
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "6px",
                      fontSize: "13px",
                      fontWeight: active ? 700 : 500,
                      color: active ? "var(--clr-primary)" : "var(--clr-text-primary)",
                    }}
                  >
                    <span>{definition.label}</span>
                    {active && <Check size={13} style={{ color: "var(--clr-primary)" }} />}
                  </span>
                  <span style={{ display: "block", fontSize: "11px", color: "var(--clr-text-muted)", whiteSpace: "normal" }}>
                    {definition.tagline}
                  </span>
                </span>
              </button>
            );
          })}
          {saving && (
            <span style={{ padding: "2px 10px", fontSize: "10px", color: "var(--clr-text-muted)" }}>
              Saving preference…
            </span>
          )}
        </div>
      )}

      {error && (
        <p style={{ margin: "4px 14px 2px 0", fontSize: "11px", color: "#fca5a5" }}>{error}</p>
      )}
    </div>
  );
}

export default DashboardStyleMenu;
