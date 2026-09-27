"use client";

import React from "react";
import Link from "next/link";
import { Activity, AlertTriangle, Lightbulb, Radar, TrendingUp } from "lucide-react";
import { AnomalyEntry, DashboardViewModel } from "../dashboardViewModel";
import { PanelVariant } from "@/lib/dashboardStyles";
import { SectionCard, formatTime, severityColors } from "./SectionCard";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";

/** Anomalies rendered with the emphasis requested by the active style. */
export function AnomalySection({ vm, variant = "summary" }: { vm: DashboardViewModel; variant?: PanelVariant }) {
  const { isAnomalyUnseen } = useNotifications();
  const limit = variant === "priority" ? 6 : 5;
  const list = vm.anomalies.slice(0, limit);
  const bySeverity = vm.anomalies.reduce(
    (acc, a) => {
      acc[a.severity] = (acc[a.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  const anomaliesHref = vm.organisationId
    ? `/anomalies?org=${encodeURIComponent(vm.organisationId)}`
    : "/anomalies";

  return (
    <SectionCard
      data-section="anomalies"
      title={variant === "priority" ? "Priority Queue" : variant === "trend" ? "Anomaly Trend" : "Detected Anomalies"}
      subtitle={
        variant === "trend"
          ? "Anomalies plotted on the metric timeline"
          : Object.entries(bySeverity)
              .map(([sev, count]) => `${count} ${sev}`)
              .join(" · ") || "Sensors are operating within normal baseline ranges"
      }
      icon={<AlertTriangle size={18} color="var(--clr-warning)" />}
      action={
        <Link href={anomaliesHref} style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-primary)" }}>
          View all →
        </Link>
      }
    >
      {list.length === 0 ? (
        <div style={{ padding: "12px", textAlign: "center", color: "#34d399", fontSize: "13px", fontWeight: 600 }}>
          ✓ No active anomalies
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {list.map((a: AnomalyEntry) => {
            const colors = severityColors(a.severity);
            const isUnseen = isAnomalyUnseen(a.id);
            return (
              <div
                key={a.id}
                style={{
                  padding: variant === "priority" ? "10px 12px" : "12px 14px",
                  borderRadius: "10px",
                  background: variant === "priority" ? colors.bg : "var(--clr-surface-2)",
                  border: `1px solid ${variant === "priority" ? colors.border : "var(--clr-border-light)"}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "10px",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "3px", flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 700, fontSize: "13px" }}>{a.label}</span>
                    {isUnseen && <RedDotIndicator size="sm" label="New unread anomaly" />}
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 800,
                        padding: "1px 8px",
                        borderRadius: "10px",
                        background: colors.bg,
                        color: colors.fg,
                        border: `1px solid ${colors.border}`,
                      }}
                    >
                      {a.severity}
                    </span>
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)" }}>
                    Value: <strong>{a.value ?? "—"} {a.unit}</strong>
                    {a.expectedMin != null && a.expectedMax != null ? ` (Expected: ${a.expectedMin}–${a.expectedMax})` : ""}
                  </div>
                </div>
                <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", whiteSpace: "nowrap" }}>{formatTime(a.timestamp)}</span>
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

/** AI recommendations rendered with the emphasis requested by the active style. */
export function RecommendationSection({ vm, variant = "summary" }: { vm: DashboardViewModel; variant?: PanelVariant }) {
  const list = variant === "table" ? vm.recommendations : vm.recommendations.slice(0, variant === "actions" ? 5 : 3);

  const recsHref = vm.organisationId
    ? `/recommendations?org=${encodeURIComponent(vm.organisationId)}`
    : "/recommendations";

  return (
    <SectionCard
      data-section="recommendations"
      title={variant === "actions" ? "Action Plans" : "AI Recommendations"}
      subtitle={variant === "actions" ? "Prioritised actions for operators" : "Generated optimisation guidance"}
      icon={<Lightbulb size={18} color="var(--clr-primary)" />}
      action={
        <Link href={recsHref} style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-primary)" }}>
          View board →
        </Link>
      }
    >
      {list.length === 0 ? (
        <div style={{ fontSize: "13px", color: "var(--clr-text-muted)" }}>No open recommendations.</div>
      ) : variant === "table" ? (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ textAlign: "left", color: "var(--clr-text-muted)", fontSize: "11px", textTransform: "uppercase" }}>
                <th style={{ padding: "8px 10px", fontWeight: 700 }}>Priority</th>
                <th style={{ padding: "8px 10px", fontWeight: 700 }}>Recommendation</th>
                <th style={{ padding: "8px 10px", fontWeight: 700 }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {list.map((rec) => {
                const colors = severityColors(rec.priority);
                return (
                  <tr key={rec.id} style={{ borderTop: "1px solid var(--clr-border-light)" }}>
                    <td style={{ padding: "10px", color: colors.fg, fontWeight: 700 }}>{rec.priority}</td>
                    <td style={{ padding: "10px" }}>
                      <div style={{ fontWeight: 700 }}>{rec.title}</div>
                      <div style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>{rec.description}</div>
                    </td>
                    <td style={{ padding: "10px", color: "var(--clr-text-secondary)" }}>{rec.actions[0]}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {list.map((rec) => {
            const colors = severityColors(rec.priority);
            return (
              <div
                key={rec.id}
                style={{
                  padding: "14px",
                  borderRadius: "10px",
                  background: "var(--clr-primary-light)",
                  border: "1px solid var(--clr-border)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", marginBottom: "6px" }}>
                  <span style={{ fontWeight: 700, fontSize: "14px", color: "var(--clr-primary-dark)" }}>{rec.title}</span>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 800,
                      padding: "1px 8px",
                      borderRadius: "10px",
                      background: colors.bg,
                      color: colors.fg,
                      border: `1px solid ${colors.border}`,
                    }}
                  >
                    {rec.priority}
                  </span>
                </div>
                {rec.description && (
                  <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: "0 0 8px 0" }}>{rec.description}</p>
                )}
                <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--clr-primary-dark)" }}>
                  💡 Action: {rec.actions[0]}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

/** Forecast panel (same forecast data in every style). */
export function ForecastSection({ vm, inline = false }: { vm: DashboardViewModel; inline?: boolean }) {
  const forecast = vm.forecast;
  const max = forecast.available ? Math.max(...forecast.points.map((p) => p.value)) : 0;

  if (inline) {
    return (
      <div
        data-section="forecast"
        style={{ display: "flex", flexDirection: "column", gap: "10px" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Radar size={16} color="#38bdf8" />
          <h2 style={{ fontSize: "14px", fontWeight: 800, margin: 0, color: "var(--clr-text-primary)" }}>Forecast</h2>
        </div>
        {forecast.available ? (
          <div style={{ display: "flex", alignItems: "flex-end", gap: "4px", height: "80px" }}>
            {forecast.points.slice(0, 12).map((p, i) => (
              <div
                key={i}
                title={`${p.label}: ${p.value} ${p.unit}`}
                style={{
                  flex: 1,
                  height: `${max > 0 ? Math.max(6, (p.value / max) * 100) : 6}%`,
                  borderRadius: "3px 3px 0 0",
                  background: "linear-gradient(180deg, #38bdf8 0%, rgba(56,189,248,0.35) 100%)",
                }}
              />
            ))}
          </div>
        ) : (
          <p style={{ fontSize: "12px", color: "var(--clr-text-muted)", margin: 0 }}>{forecast.message}</p>
        )}
      </div>
    );
  }

  const forecastHref = vm.organisationId
    ? `/forecast?org=${encodeURIComponent(vm.organisationId)}`
    : "/forecast";

  return (
    <SectionCard
      data-section="forecast"
      title="Forecast"
      subtitle={forecast.metric ? `${forecast.metric} · short-horizon prediction` : "Short-horizon prediction"}
      icon={<Radar size={18} color="#38bdf8" />}
      action={
        <Link href={forecastHref} style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-primary)" }}>
          Forecast centre →
        </Link>
      }
    >
      {!forecast.available ? (
        <p style={{ fontSize: "13px", color: "var(--clr-text-muted)", margin: 0 }}>{forecast.message}</p>
      ) : (
        <>
          <div style={{ display: "flex", alignItems: "flex-end", gap: "4px", height: "150px", marginBottom: "8px" }}>
            {forecast.points.map((p, i) => (
              <div
                key={i}
                title={`${p.label}: ${p.value} ${p.unit}`}
                style={{
                  flex: 1,
                  height: `${max > 0 ? Math.max(6, (p.value / max) * 100) : 6}%`,
                  borderRadius: "4px 4px 0 0",
                  background: "linear-gradient(180deg, #38bdf8 0%, rgba(56,189,248,0.3) 100%)",
                }}
              />
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--clr-text-muted)" }}>
            <span>{forecast.points[0]?.label}</span>
            <span>Peak {Math.max(...forecast.points.map((p) => p.value)).toLocaleString()} {forecast.unit}</span>
            <span>{forecast.points[forecast.points.length - 1]?.label}</span>
          </div>
        </>
      )}
    </SectionCard>
  );
}

/** Historical trend panel (Analytics / Command Center). */
export function TrendSection({ vm }: { vm: DashboardViewModel }) {
  const trend = vm.trend;
  if (!trend.available) {
    return (
      <SectionCard data-section="analytics-trend" title="Historical Trend" icon={<TrendingUp size={18} color="#38bdf8" />}>
        <p style={{ fontSize: "13px", color: "var(--clr-text-muted)", margin: 0 }}>
          Not enough history for a trend line yet. Readings accumulate automatically from the simulator or IoT devices.
        </p>
      </SectionCard>
    );
  }

  const points = trend.points.slice(-60);
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const width = 100;
  const height = 34;
  const coords = points
    .map((p, i) => {
      const x = (i / Math.max(1, points.length - 1)) * width;
      const y = height - ((p.value - min) / span) * height;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return (
    <SectionCard
      data-section="analytics-trend"
      title="Historical Trend"
      subtitle={`${trend.metric} · last ${points.length} readings (${trend.unit})`}
      icon={<TrendingUp size={18} color="#38bdf8" />}
    >
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: "100%", height: "160px" }}>
        <polyline points={coords} fill="none" stroke="#38bdf8" strokeWidth="0.6" vectorEffect="non-scaling-stroke" />
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "8px" }}>
        <span>Min {min.toLocaleString()} {trend.unit}</span>
        <span>Max {max.toLocaleString()} {trend.unit}</span>
        <span>
          {new Date(points[0].timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} →{" "}
          {new Date(points[points.length - 1].timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </SectionCard>
  );
}

/** Live telemetry feed (Operations / Analytics). */
export function RecentActivitySection({ vm, dense = false }: { vm: DashboardViewModel; dense?: boolean }) {
  const readings = dense ? vm.recentReadings.slice(0, 6) : vm.recentReadings;
  return (
    <SectionCard
      data-section="recent-activity"
      title={dense ? "Live Feed" : "Recent Activity Timeline"}
      subtitle="Live telemetry log"
      icon={<Activity size={18} color="#38bdf8" />}
    >
      {readings.length === 0 ? (
        <div style={{ fontSize: "13px", color: "var(--clr-text-muted)" }}>
          No recent activity. Simulator or IoT devices have not submitted recent pings.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "10px",
          }}
        >
          {readings.map((r) => (
            <div
              key={r.id}
              style={{
                padding: "10px 12px",
                borderRadius: "8px",
                backgroundColor: "var(--clr-surface-2)",
                border: "1px solid var(--clr-border-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: r.isAnomaly ? "#ef4444" : "#10b981",
                    flexShrink: 0,
                  }}
                />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, textTransform: "capitalize" }}>
                    {r.sensorType || "sensor"} reading
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--clr-text-secondary)" }}>
                    {r.value ?? "—"} {r.unit} ({r.source})
                  </div>
                </div>
              </div>
              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", whiteSpace: "nowrap" }}>{formatTime(r.timestamp)}</span>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
