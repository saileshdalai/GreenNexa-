"use client";

import React, { useState } from "react";
import { Check, ChevronDown, Palette } from "lucide-react";
import { useTheme, COLOR_THEMES } from "@/context/ThemeContext";

export function ThemeColorMenu({ onSelected }: { onSelected?: (theme: string) => void }) {
  const { colorTheme, setColorTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);

  const activeTheme = COLOR_THEMES.find((t) => t.id === colorTheme) || COLOR_THEMES[0];

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
        id="header-menu-theme-color"
        title="Choose Theme / Colour"
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
          <Palette size={15} style={{ color: activeTheme.swatch, flexShrink: 0 }} />
          <span style={{ fontSize: "13px", fontWeight: 500 }}>Theme / Colour</span>
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              padding: "2px 7px",
              borderRadius: "999px",
              fontSize: "11px",
              fontWeight: 700,
              background: "var(--clr-primary-light)",
              color: "var(--clr-primary)",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: activeTheme.swatch,
                display: "inline-block",
              }}
            />
            {activeTheme.label}
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
          aria-label="Theme / Colour Options"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "2px",
            padding: "4px 6px",
            background: "var(--clr-surface-2)",
            borderRadius: "8px",
            margin: "2px 0 4px 10px",
            borderLeft: `2px solid ${activeTheme.swatch}`,
          }}
        >
          {COLOR_THEMES.map((item) => {
            const active = item.id === colorTheme;
            return (
              <button
                key={item.id}
                type="button"
                role="menuitemradio"
                aria-checked={active}
                data-theme-color-option={item.id}
                onClick={(e) => {
                  e.stopPropagation();
                  setColorTheme(item.id);
                  onSelected?.(item.id);
                }}
                title={`Set theme color to ${item.label}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "7px 10px",
                  background: active ? "var(--clr-primary-light)" : "transparent",
                  border: "none",
                  borderRadius: "6px",
                  cursor: "pointer",
                  textAlign: "left",
                  fontFamily: "inherit",
                  fontSize: "13px",
                  fontWeight: active ? 700 : 500,
                  color: active ? "var(--clr-primary)" : "var(--clr-text-primary)",
                  transition: "all 0.15s ease",
                }}
              >
                <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      background: item.swatch,
                      boxShadow: active ? `0 0 0 2px var(--clr-surface), 0 0 0 3px ${item.swatch}` : "none",
                      flexShrink: 0,
                    }}
                  />
                  <span>{item.label}</span>
                </span>
                {active && <Check size={14} style={{ color: "var(--clr-primary)" }} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default ThemeColorMenu;
