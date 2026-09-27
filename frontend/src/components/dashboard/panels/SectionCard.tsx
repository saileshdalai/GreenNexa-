import React from "react";
import { OperationalStatus } from "../dashboardViewModel";

export const STATUS_COLORS: Record<OperationalStatus, { fg: string; bg: string; border: string; label: string }> = {
  normal: { fg: "#34d399", bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", label: "Normal" },
  warning: { fg: "#fbbf24", bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)", label: "Warning" },
  critical: { fg: "#fca5a5", bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.32)", label: "Critical" },
  nodata: { fg: "var(--clr-text-muted)", bg: "var(--clr-surface-2)", border: "var(--clr-border)", label: "No data" },
};

export function severityColors(severity: string) {
  const s = String(severity || "").toUpperCase();
  if (s === "CRITICAL") return STATUS_COLORS.critical;
  if (s === "HIGH" || s === "MEDIUM" || s === "WARNING") return STATUS_COLORS.warning;
  if (s === "LOW" || s === "NORMAL" || s === "INFO") return STATUS_COLORS.normal;
  return STATUS_COLORS.nodata;
}

export function formatTime(value?: string | null): string {
  if (!value) return "—";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "—";
  return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "—";
  return dt.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

interface SectionCardProps {
  title: string;
  icon?: React.ReactNode;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  style?: React.CSSProperties;
  id?: string;
  "data-section"?: string;
}

/** Shared section shell so every dashboard style renders identical data consistently. */
export function SectionCard({ title, icon, subtitle, action, children, style, id, ...rest }: SectionCardProps) {
  return (
    <section className="card" id={id} data-section={rest["data-section"]} style={{ padding: "20px", ...style }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "12px",
          marginBottom: "16px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
          {icon}
          <div style={{ minWidth: 0 }}>
            <h2
              style={{
                fontSize: "16px",
                fontWeight: 800,
                color: "var(--clr-text-primary)",
                margin: 0,
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              {title}
            </h2>
            {subtitle && (
              <p style={{ fontSize: "12px", color: "var(--clr-text-muted)", margin: "2px 0 0 0" }}>{subtitle}</p>
            )}
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
