"use client";

/**
 * GreenNexa — Dashboard Renderer.
 *
 * Single entry point that maps the selected dashboard style to its layout.
 * Every layout consumes the same view model, so switching style can never
 * change data, permissions, Demo Mode, the simulator or enabled modules.
 */

import React from "react";
import { DashboardStyle, getStyleDefinition, normaliseDashboardStyle } from "@/lib/dashboardStyles";
import { DashboardViewModel } from "./dashboardViewModel";
import { ExecutiveLayout } from "./layouts/ExecutiveLayout";
import { OperationsLayout } from "./layouts/OperationsLayout";
import { AnalyticsLayout } from "./layouts/AnalyticsLayout";
import { CommandCenterLayout } from "./layouts/CommandCenterLayout";

export interface DashboardRendererProps {
  vm: DashboardViewModel;
  style?: DashboardStyle | string | null;
  onSelectOrg?: (id: string, name: string) => void;
}

export function DashboardRenderer({ vm, style, onSelectOrg }: DashboardRendererProps) {
  const resolved = normaliseDashboardStyle(style);
  const definition = getStyleDefinition(resolved);
  const props = { vm, onSelectOrg };

  return (
    <div
      data-dashboard-style={resolved}
      data-dashboard-style-label={definition.label}
      aria-label={`${definition.label} dashboard layout`}
    >
      {resolved === "EXECUTIVE" && <ExecutiveLayout {...props} />}
      {resolved === "OPERATIONS" && <OperationsLayout {...props} />}
      {resolved === "ANALYTICS" && <AnalyticsLayout {...props} />}
      {resolved === "COMMAND_CENTER" && <CommandCenterLayout {...props} />}
    </div>
  );
}

export default DashboardRenderer;
