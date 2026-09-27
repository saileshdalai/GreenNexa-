"use client";

/**
 * ANALYTICS — analyse the data deeply.
 * Metric matrix and trend charts lead; anomaly/recommendation panels switch to
 * trend and table variants; wide two-column reading layout.
 */

import React from "react";
import { DashboardSection, composeRows, getStyleDefinition, resolveSections } from "@/lib/dashboardStyles";
import { DashboardLayoutProps } from "./ExecutiveLayout";
import { SectionSlot } from "./SectionSlot";

const STYLE = "ANALYTICS";

const SHARE_ROW: DashboardSection[] = [
  "analytics-trend",
  "forecast",
  "anomalies",
  "recommendations",
  "analytics-metrics",
  "insights",
  "critical-alerts",
  "modules",
  "ward-status",
  "associated-orgs",
  "recent-activity",
  "spatial-overview",
];

export function AnalyticsLayout({ vm, onSelectOrg }: DashboardLayoutProps) {
  const definition = getStyleDefinition(STYLE);
  const rows = composeRows(resolveSections(STYLE, vm.capabilities), { shareRow: SHARE_ROW, groupSize: 2 });

  return (
    <div
      data-dashboard-layout={STYLE}
      style={{ display: "flex", flexDirection: "column", gap: definition.grid.gap, maxWidth: "1600px" }}
    >
      {rows.map((row, rowIndex) =>
        row.length === 1 ? (
          <SectionSlot key={row[0]} section={row[0]} vm={vm} style={STYLE} onSelectOrg={onSelectOrg} />
        ) : (
          <div
            key={`row-${rowIndex}`}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: definition.grid.gap }}
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

export default AnalyticsLayout;
