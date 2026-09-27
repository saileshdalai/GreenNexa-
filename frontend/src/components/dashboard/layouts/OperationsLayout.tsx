"use client";

/**
 * OPERATIONS — show me what needs attention now.
 * Action rail first, dense live metrics, priority queue up top, compact panels.
 */

import React from "react";
import { DashboardSection, composeRows, getStyleDefinition, resolveSections } from "@/lib/dashboardStyles";
import { DashboardLayoutProps } from "./ExecutiveLayout";
import { SectionSlot } from "./SectionSlot";

const STYLE = "OPERATIONS";

const SHARE_ROW: DashboardSection[] = [
  "anomalies",
  "critical-alerts",
  "recommendations",
  "insights",
  "forecast",
  "modules",
  "ward-status",
  "associated-orgs",
  "recent-activity",
  "spatial-overview",
  "analytics-trend",
  "analytics-metrics",
];

export function OperationsLayout({ vm, onSelectOrg }: DashboardLayoutProps) {
  const definition = getStyleDefinition(STYLE);
  const rows = composeRows(resolveSections(STYLE, vm.capabilities), { shareRow: SHARE_ROW, groupSize: 2 });

  return (
    <div
      data-dashboard-layout={STYLE}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: definition.grid.gap,
        padding: "16px",
        borderRadius: "16px",
        background: "var(--clr-surface-2, rgba(148,163,184,0.04))",
        border: "1px solid var(--clr-border-light, var(--clr-border))",
      }}
    >
      {rows.map((row, rowIndex) =>
        row.length === 1 ? (
          <SectionSlot key={row[0]} section={row[0]} vm={vm} style={STYLE} onSelectOrg={onSelectOrg} />
        ) : (
          <div
            key={`row-${rowIndex}`}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: definition.grid.gap }}
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

export default OperationsLayout;
