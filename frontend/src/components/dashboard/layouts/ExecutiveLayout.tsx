"use client";

/**
 * EXECUTIVE — understand the situation quickly.
 * Health strip and hero KPIs lead; everything else is calm, wide and paired.
 */

import React from "react";
import { DashboardSection, composeRows, getStyleDefinition, resolveSections } from "@/lib/dashboardStyles";
import { DashboardViewModel } from "../dashboardViewModel";
import { SectionSlot } from "./SectionSlot";

export interface DashboardLayoutProps {
  vm: DashboardViewModel;
  /** Optional interaction hooks supplied by the host dashboard. */
  onSelectOrg?: (id: string, name: string) => void;
}

const SHARE_ROW: DashboardSection[] = [
  "critical-alerts",
  "insights",
  "anomalies",
  "recommendations",
  "forecast",
  "analytics-trend",
  "analytics-metrics",
  "modules",
  "ward-status",
  "associated-orgs",
  "recent-activity",
  "spatial-overview",
];

export function ExecutiveLayout({ vm, onSelectOrg }: DashboardLayoutProps) {
  const style = "EXECUTIVE";
  const definition = getStyleDefinition(style);
  const rows = composeRows(resolveSections(style, vm.capabilities), { shareRow: SHARE_ROW, groupSize: 2 });

  return (
    <div
      data-dashboard-layout={style}
      style={{ display: "flex", flexDirection: "column", gap: definition.grid.gap, maxWidth: "1400px" }}
    >
      {rows.map((row, rowIndex) =>
        row.length === 1 ? (
          <SectionSlot
            key={row[0]}
            section={row[0]}
            vm={vm}
            style={style}
            onSelectOrg={onSelectOrg}
          />
        ) : (
          <div
            key={`row-${rowIndex}`}
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: definition.grid.gap }}
          >
            {row.map((section) => (
              <SectionSlot
                key={section}
                section={section}
                vm={vm}
                style={style}
                onSelectOrg={onSelectOrg}
              />
            ))}
          </div>
        )
      )}
    </div>
  );
}

export default ExecutiveLayout;
