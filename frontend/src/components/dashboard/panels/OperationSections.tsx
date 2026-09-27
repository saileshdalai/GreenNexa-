"use client";

import React from "react";
import Link from "next/link";
import { Building2, Eye, Layers, Map, MapPin, Navigation, Zap } from "lucide-react";
import { DashboardViewModel } from "../dashboardViewModel";
import { SectionCard, STATUS_COLORS } from "./SectionCard";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";

/** Quick action rail (Operations / Command Center). */
export function QuickActionsSection({ vm, inline = false }: { vm: DashboardViewModel; inline?: boolean }) {
  if (inline) {
    return (
      <div data-section="quick-actions" style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
        {vm.quickActions.map((action) => (
          <Link
            key={action.id}
            href={action.href}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "7px 12px",
              borderRadius: "20px",
              fontSize: "12px",
              fontWeight: 700,
              textDecoration: "none",
              background:
                action.tone === "warning"
                  ? "rgba(245,158,11,0.12)"
                  : action.tone === "primary"
                  ? "var(--clr-primary-light)"
                  : "var(--clr-surface-2)",
              color: action.tone === "warning" ? "#fbbf24" : "var(--clr-primary)",
              border: `1px solid ${action.tone === "warning" ? "rgba(245,158,11,0.3)" : "var(--clr-border)"}`,
            }}
          >
            <Zap size={13} />
            {action.label}
          </Link>
        ))}
      </div>
    );
  }

  return (
    <SectionCard
      data-section="quick-actions"
      title="Quick Actions"
      subtitle="Jump straight into the workflows you use most"
      icon={<Zap size={18} color="var(--clr-primary)" />}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
        {vm.quickActions.map((action) => (
          <Link
            key={action.id}
            href={action.href}
            className="btn btn-outline btn-sm"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              textDecoration: "none",
              borderColor: action.tone === "warning" ? "rgba(245,158,11,0.4)" : undefined,
              color: action.tone === "warning" ? "#fbbf24" : undefined,
            }}
          >
            {action.label}
          </Link>
        ))}
      </div>
    </SectionCard>
  );
}

/** Enabled module / operational scope grid (municipality civic modules or facility modules). */
export function ModuleSection({ vm }: { vm: DashboardViewModel }) {
  const { isModuleUnread } = useNotifications();
  return (
    <SectionCard
      data-section="modules"
      title={vm.isMunicipality ? "Municipal Operations Control Center" : "Operational Modules"}
      subtitle="Live telemetry summaries per enabled module"
      icon={<Layers size={18} color="var(--clr-primary)" />}
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "12px" }}>
        {vm.modules.map((mod) => {
          const status = STATUS_COLORS[mod.status];
          const hasUnread = isModuleUnread(mod.id);
          return (
            <Link
              key={mod.id}
              href={mod.href}
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                padding: "14px 16px",
                borderRadius: "12px",
                background: "var(--clr-surface-2, rgba(255,255,255,0.03))",
                border: `1px solid ${mod.status === "normal" ? "var(--clr-border, #334155)" : status.border}`,
                textDecoration: "none",
                gap: "10px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
                  <span style={{ fontSize: "18px", padding: "5px", borderRadius: "8px", background: mod.background }}>{mod.icon}</span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-text-primary)" }}>{mod.label}</div>
                      {hasUnread && <RedDotIndicator size="sm" label={`${mod.label} — unread anomaly`} />}
                    </div>
                    <div style={{ fontSize: "10px", color: "var(--clr-text-muted)" }}>Operational scope</div>
                  </div>
                </div>
                <span
                  style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "10px",
                    textTransform: "uppercase",
                    background: status.bg,
                    color: status.fg,
                    border: `1px solid ${status.border}`,
                    whiteSpace: "nowrap",
                  }}
                >
                  {status.label}
                </span>
              </div>

              <div>
                {mod.hasData ? (
                  <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
                    <span style={{ fontSize: "20px", fontWeight: 800, color: mod.color }}>{mod.displayValue}</span>
                    <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--clr-text-muted)" }}>{mod.unit}</span>
                  </div>
                ) : (
                  <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", fontStyle: "italic" }}>
                    No current data <span style={{ fontSize: "10px", opacity: 0.7 }}>(waiting for sensor data)</span>
                  </div>
                )}
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "11px",
                  borderTop: "1px solid var(--clr-border, #334155)",
                  paddingTop: "8px",
                }}
              >
                <span style={{ color: mod.anomaliesCount > 0 ? "#fbbf24" : "var(--clr-text-muted)", fontWeight: mod.anomaliesCount > 0 ? 700 : 500 }}>
                  {mod.anomaliesCount > 0
                    ? `⚠️ ${mod.anomaliesCount} active anomal${mod.anomaliesCount === 1 ? "y" : "ies"}`
                    : "✓ 0 anomalies"}
                </span>
                {mod.hasData && (
                  <span style={{ color: mod.trendLabel.startsWith("+") ? "#34d399" : "#60a5fa", fontWeight: 600 }}>
                    {mod.trendLabel} trend
                  </span>
                )}
              </div>
            </Link>
          );
        })}
      </div>
    </SectionCard>
  );
}

/** Ward status list (municipality). */
export function WardStatusSection({ vm, limit }: { vm: DashboardViewModel; limit?: number }) {
  const wards = limit ? vm.wards.slice(0, limit) : vm.wards;
  return (
    <SectionCard
      data-section="ward-status"
      title="Ward Operations"
      subtitle="Administrative wards under this municipality"
      icon={<MapPin size={18} color="var(--clr-primary)" />}
    >
      {wards.length === 0 ? (
        <div style={{ fontSize: "13px", color: "var(--clr-text-muted)" }}>
          No wards configured. Use Add → Ward from the options menu to create wards for this municipality.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "10px" }}>
          {wards.map((ward) => {
            const status = STATUS_COLORS[ward.status];
            return (
              <Link
                key={ward.id}
                href={ward.href}
                style={{
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "12px 14px",
                  borderRadius: "10px",
                  background: "var(--clr-surface-2)",
                  border: `1px solid ${ward.status === "normal" ? "var(--clr-border)" : status.border}`,
                  textDecoration: "none",
                }}
              >
                {ward.hasUnread && (
                  <div style={{ position: "absolute", top: "8px", right: "8px" }}>
                    <RedDotIndicator size="sm" label="Ward — unread anomaly" />
                  </div>
                )}
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    borderRadius: "8px",
                    background: "var(--clr-primary-light)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <Layers size={15} color="var(--clr-primary)" />
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-text-primary)" }}>{ward.wardName}</div>
                  <div style={{ fontSize: "11px", color: status.fg, fontFamily: "monospace" }}>
                    Ward {ward.wardNumber} · {status.label}
                    {ward.alertsCount > 0 ? ` · ${ward.alertsCount}` : ""}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

/** Spatial / coverage overview (Command Center lead). */
export function SpatialOverviewSection({ vm }: { vm: DashboardViewModel }) {
  const modules = vm.modules;
  const healthy = modules.filter((m) => m.status === "normal").length;
  const warning = modules.filter((m) => m.status === "warning").length;
  const critical = modules.filter((m) => m.status === "critical").length;
  const wardCoverage = vm.totalWards;

  return (
    <SectionCard
      data-section="spatial-overview"
      title="Operational Coverage"
      subtitle="Spatial status across modules and wards"
      icon={<Map size={18} color="var(--clr-primary)" />}
      style={{ background: "linear-gradient(135deg, rgba(56,189,248,0.06) 0%, transparent 60%)" }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "12px", marginBottom: "16px" }}>
        {[
          { label: "Modules healthy", value: healthy, color: "#34d399" },
          { label: "Modules degraded", value: warning, color: "#fbbf24" },
          { label: "Modules critical", value: critical, color: "#fca5a5" },
          { label: vm.isMunicipality ? "Wards covered" : "Sensors tracked", value: vm.isMunicipality ? wardCoverage : vm.kpis.length, color: "#38bdf8" },
        ].map((item) => (
          <div key={item.label} style={{ padding: "12px 14px", borderRadius: "10px", background: "var(--clr-surface-2)", border: "1px solid var(--clr-border)" }}>
            <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>{item.label}</div>
            <div style={{ fontSize: "24px", fontWeight: 800, color: item.color }}>{item.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {modules.slice(0, 8).map((mod) => {
          const status = STATUS_COLORS[mod.status];
          return (
            <div key={mod.id} style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "12px" }}>
              <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: status.fg, flexShrink: 0 }} />
              <span style={{ fontWeight: 700, color: "var(--clr-text-primary)", flex: 1, minWidth: 0 }}>{mod.label}</span>
              <span style={{ color: "var(--clr-text-muted)" }}>
                {mod.hasData ? `${mod.displayValue} ${mod.unit}` : "no data"}
              </span>
            </div>
          );
        })}
      </div>

      {vm.isMunicipality && vm.wards.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "14px", fontSize: "11px", color: "var(--clr-text-muted)" }}>
          <Navigation size={12} />
          Drill into a ward to inspect its own modules, anomalies and recommendations.
        </div>
      )}
    </SectionCard>
  );
}

/** Associated government organisations (municipality, read-only). */
export function AssociatedOrgsSection({ vm, onSelect }: { vm: DashboardViewModel; onSelect?: (id: string, name: string) => void }) {
  return (
    <SectionCard
      data-section="associated-orgs"
      title="Associated Government Organisations"
      subtitle="Read-only operational summaries"
      icon={<Building2 size={18} color="var(--clr-primary)" />}
    >
      {vm.associatedOrgs.length === 0 ? (
        <div style={{ fontSize: "13px", color: "var(--clr-text-muted)" }}>
          No organisations associated. Use Add → Organisation from the options menu to associate government organisations.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {vm.associatedOrgs.map((org) => (
            <div
              key={org.id}
              role={onSelect ? "button" : undefined}
              tabIndex={onSelect ? 0 : undefined}
              onClick={() => onSelect?.(org.id, org.name)}
              onKeyDown={(e) => {
                if (onSelect && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  onSelect(org.id, org.name);
                }
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
                padding: "14px 16px",
                borderRadius: "10px",
                background: "var(--clr-surface-2)",
                border: "1px solid var(--clr-border)",
                cursor: onSelect ? "pointer" : "default",
              }}
            >
              <div
                style={{
                  width: "38px",
                  height: "38px",
                  borderRadius: "9px",
                  background: "var(--clr-primary-light)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <Building2 size={18} color="var(--clr-primary)" />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: "14px",
                    fontWeight: 700,
                    color: "var(--clr-text-primary)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {org.name}
                </div>
                <div style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>
                  {org.orgType}
                  {org.location ? ` · ${org.location}` : ""}
                </div>
              </div>
              {onSelect && <Eye size={14} color="var(--clr-text-muted)" />}
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
