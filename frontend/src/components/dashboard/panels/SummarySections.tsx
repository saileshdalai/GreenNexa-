"use client";

import React from "react";
import Link from "next/link";
import { Activity, AlertTriangle, Cpu, Droplet, Gauge, LineChart, ShieldCheck, Thermometer, Trash2, Zap } from "lucide-react";
import { DashboardViewModel, KpiEntry } from "../dashboardViewModel";
import { KpiEmphasis } from "@/lib/dashboardStyles";
import { SectionCard, STATUS_COLORS, severityColors } from "./SectionCard";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";

const KPI_ICONS: Record<string, React.ReactNode> = {
  energy: <Zap size={18} />,
  water: <Droplet size={18} />,
  waste: <Trash2 size={18} />,
  temperature: <Thermometer size={18} />,
  climate: <Thermometer size={18} />,
  air_quality: <Activity size={18} />,
  co2: <Activity size={18} />,
  humidity: <Activity size={18} />,
  assets: <Cpu size={18} />,
  equipment_asset: <Cpu size={18} />,
  safety: <ShieldCheck size={18} />,
  traffic: <Activity size={18} />,
  parking: <Activity size={18} />,
};

const KPI_TINTS: Record<string, string> = {
  energy: "rgba(245, 158, 11, 0.15)",
  water: "rgba(59, 130, 246, 0.15)",
  waste: "rgba(16, 185, 129, 0.15)",
  temperature: "rgba(239, 68, 68, 0.15)",
  climate: "rgba(52, 211, 153, 0.15)",
  air_quality: "rgba(168, 85, 247, 0.15)",
  co2: "rgba(168, 85, 247, 0.15)",
  humidity: "rgba(168, 85, 247, 0.15)",
  assets: "rgba(20, 184, 166, 0.15)",
  equipment_asset: "rgba(99, 102, 241, 0.15)",
  safety: "rgba(239, 68, 68, 0.15)",
  traffic: "rgba(234, 179, 8, 0.15)",
  parking: "rgba(99, 102, 241, 0.15)",
};

function limitKpis(kpis: KpiEntry[], maxCards: number | null): KpiEntry[] {
  return maxCards == null ? kpis : kpis.slice(0, maxCards);
}

/** Overall health + headline counters. */
export function HealthSummarySection({ vm, compact = false }: { vm: DashboardViewModel; compact?: boolean }) {
  const { score } = vm;
  return (
    <div
      data-section="health-summary"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: compact ? "14px 18px" : "16px 20px",
        borderRadius: "12px",
        backgroundColor: "var(--clr-surface-2)",
        border: "1px solid var(--clr-border)",
        gap: "16px",
        flexWrap: "wrap",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div
          style={{
            width: compact ? "48px" : "58px",
            height: compact ? "48px" : "58px",
            borderRadius: "50%",
            backgroundColor: `${score.color}22`,
            border: `2px solid ${score.color}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 800,
            fontSize: "1.05rem",
            color: score.color,
            flexShrink: 0,
          }}
        >
          {score.value}%
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 700, color: score.color, letterSpacing: "0.05em" }}>
              {score.label}
            </span>
            <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--clr-text-primary)" }}>
              Optimal Score: {score.value}%
            </span>
          </div>
          <p style={{ margin: "2px 0 0 0", fontSize: "0.8rem", color: "var(--clr-text-secondary)" }}>
            Methodology: Baseline 100% minus active anomaly penalties (Critical: -20%, High: -10%, Medium: -5%, Low: -2%).
          </p>
        </div>
      </div>

      <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: "0.75rem", color: "var(--clr-text-muted)" }}>Active Anomalies</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: vm.activeAnomalyCount > 0 ? "#f87171" : "#34d399" }}>
            {vm.activeAnomalyCount}
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.75rem", color: "var(--clr-text-muted)" }}>AI Action Plans</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#60a5fa" }}>{vm.recommendations.length}</div>
        </div>
        {vm.isMunicipality && (
          <>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--clr-text-muted)" }}>Wards</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#818cf8" }}>{vm.totalWards}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", color: "var(--clr-text-muted)" }}>Critical Issues</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 700, color: vm.criticalAnomalyCount > 0 ? "#fca5a5" : "#34d399" }}>
                {vm.criticalAnomalyCount}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/** KPI presentation varies per style (hero / dense / radial / table). */
export function KpiSection({
  vm,
  emphasis,
  maxCards,
}: {
  vm: DashboardViewModel;
  emphasis: KpiEmphasis;
  maxCards: number | null;
}) {
  const { isModuleUnread } = useNotifications();
  const entries = limitKpis(vm.kpis, maxCards);

  if (emphasis === "table") {
    return <AnalyticsMetricsSection vm={vm} />;
  }

  const gridTemplate =
    emphasis === "hero"
      ? "repeat(auto-fit, minmax(300px, 1fr))"
      : emphasis === "radial"
      ? "repeat(auto-fit, minmax(170px, 1fr))"
      : "repeat(auto-fit, minmax(200px, 1fr))";

  const allModulesHref = vm.organisationId
    ? `/dashboard/modules?org=${encodeURIComponent(vm.organisationId)}`
    : "/dashboard/modules";

  return (
    <SectionCard
      data-section="kpis"
      title={emphasis === "hero" ? "Key Performance Indicators" : "Live Metrics"}
      subtitle="Live telemetry — click any metric for drill-down intelligence"
      icon={<Gauge size={18} color="var(--clr-primary)" />}
      action={
        <Link href={allModulesHref} style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-primary)" }}>
          All modules →
        </Link>
      }
    >
      <div style={{ display: "grid", gridTemplateColumns: gridTemplate, gap: emphasis === "dense" ? 14 : 20 }}>
        {entries.map((kpi) => {
          const status = STATUS_COLORS[kpi.status];
          const hasUnread = isModuleUnread(kpi.key);
          const body = (
            <div
              className="card"
              style={{
                padding: emphasis === "dense" ? "14px 16px" : "18px 20px",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                height: "100%",
                borderColor: kpi.isAnomaly ? status.border : "var(--clr-border)",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontSize: emphasis === "dense" ? "12px" : "14px", fontWeight: 600, color: "var(--clr-text-secondary)" }}>
                      {kpi.title}
                    </span>
                    {hasUnread && <RedDotIndicator size="sm" label={`${kpi.title} — unread anomaly`} />}
                  </div>
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "8px",
                      backgroundColor: KPI_TINTS[kpi.key] || "rgba(100,116,139,0.15)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--clr-primary)",
                      flexShrink: 0,
                    }}
                  >
                    {KPI_ICONS[kpi.key] || <Activity size={18} />}
                  </div>
                </div>

                {emphasis === "radial" ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div
                      style={{
                        width: "46px",
                        height: "46px",
                        borderRadius: "50%",
                        background: `conic-gradient(${status.fg} ${Math.max(6, Math.min(100, kpi.readingCount ? 100 : 12))}%, var(--clr-surface-2) 0)`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <div
                        style={{
                          width: "36px",
                          height: "36px",
                          borderRadius: "50%",
                          background: "var(--clr-surface-1, var(--clr-surface))",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <span style={{ fontSize: "10px", fontWeight: 800, color: status.fg }}>
                          {kpi.readingCount > 999 ? "999+" : kpi.readingCount}
                        </span>
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                        {kpi.displayValue} <span style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>{kpi.unit}</span>
                      </div>
                      <div style={{ fontSize: "10px", color: status.fg, fontWeight: 700 }}>{status.label}</div>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
                    <span style={{ fontSize: emphasis === "dense" ? "20px" : "28px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                      {kpi.displayValue}
                    </span>
                    <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--clr-text-muted)" }}>{kpi.unit}</span>
                  </div>
                )}
              </div>

              <div
                style={{
                  marginTop: 12,
                  paddingTop: 8,
                  borderTop: "1px solid var(--clr-border-light)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "11px",
                  gap: "8px",
                }}
              >
                <span
                  style={{
                    color: status.fg,
                    fontWeight: 700,
                    padding: "1px 8px",
                    borderRadius: "10px",
                    background: status.bg,
                    border: `1px solid ${status.border}`,
                    fontSize: "10px",
                  }}
                >
                  {status.label}
                </span>
                <span style={{ color: "var(--clr-text-muted)" }}>
                  {kpi.trendPct != null ? `${kpi.trendPct >= 0 ? "+" : ""}${kpi.trendPct.toFixed(1)}% vs avg` : "Live Telemetry"}
                </span>
              </div>
            </div>
          );

          return (
            <Link key={kpi.key} href={kpi.href} style={{ textDecoration: "none", color: "inherit", display: "block" }}>
              {body}
            </Link>
          );
        })}
      </div>
      {entries.length < vm.kpis.length && (
        <p style={{ fontSize: "11px", color: "var(--clr-text-muted)", margin: "12px 0 0 0" }}>
          Showing the {entries.length} headline metrics of {vm.kpis.length} available — switch to the Analytics style for the full set.
        </p>
      )}
    </SectionCard>
  );
}

/** Analytics-style detailed metric table (same KPI data, tabular presentation). */
export function AnalyticsMetricsSection({ vm }: { vm: DashboardViewModel }) {
  return (
    <SectionCard
      data-section="analytics-metrics"
      title="Metric Matrix"
      subtitle="Every enabled sensor with statistics, deviation from baseline and reading volume"
      icon={<LineChart size={18} color="#38bdf8" />}
      style={{ overflowX: "auto" }}
    >
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
        <thead>
          <tr style={{ textAlign: "left", color: "var(--clr-text-muted)", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            <th style={{ padding: "8px 10px", fontWeight: 700 }}>Metric</th>
            <th style={{ padding: "8px 10px", fontWeight: 700 }}>Latest</th>
            <th style={{ padding: "8px 10px", fontWeight: 700 }}>Average</th>
            <th style={{ padding: "8px 10px", fontWeight: 700 }}>Min / Max</th>
            <th style={{ padding: "8px 10px", fontWeight: 700 }}>vs Avg</th>
            <th style={{ padding: "8px 10px", fontWeight: 700 }}>Readings</th>
            <th style={{ padding: "8px 10px", fontWeight: 700 }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {vm.kpis.map((kpi) => {
            const status = STATUS_COLORS[kpi.status];
            return (
              <tr key={kpi.key} style={{ borderTop: "1px solid var(--clr-border-light)" }}>
                <td style={{ padding: "10px", fontWeight: 700 }}>
                  <Link href={kpi.href} style={{ color: "var(--clr-primary)" }}>
                    {kpi.title} →
                  </Link>
                </td>
                <td style={{ padding: "10px", fontWeight: 700 }}>
                  {kpi.displayValue} {kpi.unit}
                </td>
                <td style={{ padding: "10px", color: "var(--clr-text-secondary)" }}>{kpi.average ?? "—"}</td>
                <td style={{ padding: "10px", color: "var(--clr-text-secondary)" }}>
                  {kpi.minimum ?? "—"} / {kpi.maximum ?? "—"}
                </td>
                <td
                  style={{
                    padding: "10px",
                    fontWeight: 700,
                    color: kpi.trendPct == null ? "var(--clr-text-muted)" : kpi.trendPct > 0 ? "#fbbf24" : "#60a5fa",
                  }}
                >
                  {kpi.trendPct == null ? "—" : `${kpi.trendPct >= 0 ? "+" : ""}${kpi.trendPct.toFixed(1)}%`}
                </td>
                <td style={{ padding: "10px", color: "var(--clr-text-secondary)" }}>{kpi.readingCount}</td>
                <td style={{ padding: "10px" }}>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      padding: "2px 8px",
                      borderRadius: "10px",
                      color: status.fg,
                      background: status.bg,
                      border: `1px solid ${status.border}`,
                    }}
                  >
                    {status.label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </SectionCard>
  );
}

/** Critical alert rail — anomaly data, executive/critical emphasis. */
export function CriticalAlertsSection({ vm }: { vm: DashboardViewModel }) {
  const critical = vm.anomalies.filter((a) => a.severity === "CRITICAL" || a.severity === "HIGH");
  const list = (critical.length > 0 ? critical : vm.anomalies).slice(0, 4);
  const triageHref = vm.organisationId
    ? `/anomalies?org=${encodeURIComponent(vm.organisationId)}`
    : "/anomalies";

  return (
    <SectionCard
      data-section="critical-alerts"
      title="Critical Alerts"
      subtitle={critical.length > 0 ? `${critical.length} high-priority anomalies require attention` : "No critical anomalies detected"}
      icon={<AlertTriangle size={18} color="#ef4444" />}
      action={
        <Link href={triageHref} style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-primary)" }}>
          Triage all →
        </Link>
      }
    >
      {list.length === 0 ? (
        <div style={{ padding: "12px", textAlign: "center", color: "#34d399", fontSize: "13px", fontWeight: 600 }}>
          ✓ All sensors operating within normal baseline ranges
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {list.map((a) => {
            const colors = severityColors(a.severity);
            return (
              <div
                key={a.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px",
                  padding: "12px 14px",
                  borderRadius: "10px",
                  background: colors.bg,
                  border: `1px solid ${colors.border}`,
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: colors.fg }}>
                    {a.severity} · {a.label}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)" }}>
                    {a.value ?? "—"} {a.unit} — {a.reason || "Outside expected baseline range"}
                  </div>
                </div>
                <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", whiteSpace: "nowrap" }}>
                  {a.timestamp ? new Date(a.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

/** Executive AI insight summary (derived from recommendations only). */
export function InsightSection({ vm }: { vm: DashboardViewModel }) {
  const top = vm.recommendations[0];
  const insightHref = vm.organisationId
    ? `/recommendations?org=${encodeURIComponent(vm.organisationId)}`
    : "/recommendations";

  return (
    <SectionCard
      data-section="insights"
      title="AI Insight"
      subtitle="Highest-impact generated recommendation"
      icon={<Activity size={18} color="#a78bfa" />}
      action={
        <Link href={insightHref} style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-primary)" }}>
          Insight board →
        </Link>
      }
    >
      {!top ? (
        <div style={{ fontSize: "13px", color: "var(--clr-text-muted)" }}>
          No active AI insight. Insights appear once anomaly detection has run for this organisation.
        </div>
      ) : (
        <div style={{ padding: "14px 16px", borderRadius: "10px", background: "rgba(167,139,250,0.07)", border: "1px solid rgba(167,139,250,0.2)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", marginBottom: "6px" }}>
            <span style={{ fontSize: "14px", fontWeight: 700, color: "#c4b5fd" }}>{top.title}</span>
            <span
              style={{
                fontSize: "10px",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "10px",
                background: "rgba(167,139,250,0.15)",
                color: "#c4b5fd",
                border: "1px solid rgba(167,139,250,0.3)",
              }}
            >
              {top.priority}
            </span>
          </div>
          <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: "0 0 8px 0" }}>{top.description}</p>
          <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "var(--clr-text-secondary)" }}>
            {top.actions.slice(0, 3).map((action, i) => (
              <li key={i}>{action}</li>
            ))}
          </ul>
        </div>
      )}
    </SectionCard>
  );
}
