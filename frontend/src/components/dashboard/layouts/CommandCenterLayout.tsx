"use client";

/**
 * COMMAND_CENTER — monitor the whole operation from one place.
 * Central spatial view, radial operational indicators and three-column rails of
 * alerts / wards / actions, on a darker operations canvas.
 */

import React from "react";
import { DashboardSection, composeRows, getStyleDefinition, resolveSections } from "@/lib/dashboardStyles";
import { DashboardLayoutProps } from "./ExecutiveLayout";
import { SectionSlot } from "./SectionSlot";

const STYLE = "COMMAND_CENTER";

const SHARE_ROW: DashboardSection[] = [
  "critical-alerts",
  "ward-status",
  "quick-actions",
  "insights",
  "forecast",
  "anomalies",
  "recommendations",
  "modules",
  "associated-orgs",
  "recent-activity",
  "analytics-trend",
  "analytics-metrics",
  "spatial-overview",
];

export function CommandCenterLayout({ vm, onSelectOrg }: DashboardLayoutProps) {
  const definition = getStyleDefinition(STYLE);
  const rows = composeRows(resolveSections(STYLE, vm.capabilities), { shareRow: SHARE_ROW, groupSize: 3 });

  return (
    <div
      data-dashboard-layout={STYLE}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: definition.grid.gap,
        padding: "20px",
        borderRadius: "18px",
        background:
          "radial-gradient(1200px 400px at 50% -10%, rgba(56,189,248,0.10) 0%, transparent 60%), var(--clr-surface-1, transparent)",
        border: "1px solid var(--clr-border)",
      }}
    >
      {rows.map((row, rowIndex) =>
        row.length === 1 ? (
          <SectionSlot key={row[0]} section={row[0]} vm={vm} style={STYLE} onSelectOrg={onSelectOrg} />
        ) : (
          <div
            key={`row-${rowIndex}`}
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(auto-fit, minmax(${row.length === 3 ? "280px" : "340px"}, 1fr))`,
              gap: definition.grid.gap,
            }}
          >
            {row.map((section) => (
              <SectionSlot key={section} section={section} vm={vm} style={STYLE} onSelectOrg={onSelectOrg} />
            ))}
          </div>
        )
      )}
    </div>
  );
}

export default CommandCenterLayout;
