"use client";

/**
 * GreenNexa — shared section renderer.
 *
 * Maps one resolved section to its panel, applying the presentation emphasis of
 * the active style (KPI emphasis, panel variant, compact vs. inline chrome).
 * The data always comes from the shared view model, so the only thing the style
 * changes here is presentation.
 */

import React from "react";
import { DashboardSection, getKpiEmphasis, getSectionVariant, getStyleDefinition, normaliseDashboardStyle } from "@/lib/dashboardStyles";
import { DashboardViewModel } from "../dashboardViewModel";
import {
  AnalyticsMetricsSection,
  CriticalAlertsSection,
  HealthSummarySection,
  InsightSection,
  KpiSection,
} from "../panels/SummarySections";
import {
  AnomalySection,
  ForecastSection,
  RecentActivitySection,
  RecommendationSection,
  TrendSection,
} from "../panels/IntelligenceSections";
import {
  AssociatedOrgsSection,
  ModuleSection,
  QuickActionsSection,
  SpatialOverviewSection,
  WardStatusSection,
} from "../panels/OperationSections";

export interface SectionSlotProps {
  section: DashboardSection;
  vm: DashboardViewModel;
  style: string;
  onSelectOrg?: (id: string, name: string) => void;
}

export function SectionSlot({ section, vm, style, onSelectOrg }: SectionSlotProps) {
  const resolved = normaliseDashboardStyle(style);
  const definition = getStyleDefinition(resolved);

  switch (section) {
    case "health-summary":
      return <HealthSummarySection vm={vm} compact={resolved !== "EXECUTIVE"} />;
    case "kpis":
      return <KpiSection vm={vm} emphasis={getKpiEmphasis(resolved)} maxCards={definition.kpi.maxCards} />;
    case "critical-alerts":
      return <CriticalAlertsSection vm={vm} />;
    case "insights":
      return <InsightSection vm={vm} />;
    case "forecast":
      return <ForecastSection vm={vm} inline={resolved === "OPERATIONS" || resolved === "COMMAND_CENTER"} />;
    case "anomalies":
      return <AnomalySection vm={vm} variant={getSectionVariant(resolved, "anomalies")} />;
    case "recommendations":
      return <RecommendationSection vm={vm} variant={getSectionVariant(resolved, "recommendations")} />;
    case "quick-actions":
      return <QuickActionsSection vm={vm} inline={resolved === "EXECUTIVE" || resolved === "ANALYTICS"} />;
    case "recent-activity":
      return <RecentActivitySection vm={vm} dense={resolved === "OPERATIONS" || resolved === "COMMAND_CENTER"} />;
    case "analytics-metrics":
      return <AnalyticsMetricsSection vm={vm} />;
    case "analytics-trend":
      return <TrendSection vm={vm} />;
    case "modules":
      return <ModuleSection vm={vm} />;
    case "ward-status":
      return <WardStatusSection vm={vm} />;
    case "spatial-overview":
      return <SpatialOverviewSection vm={vm} />;
    case "associated-orgs":
      return <AssociatedOrgsSection vm={vm} onSelect={onSelectOrg} />;
    default:
      return null;
  }
}

export default SectionSlot;
