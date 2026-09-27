/**
 * GreenNexa — Dashboard Style System (authoritative style registry).
 *
 * The dashboard style is a PRESENTATION preference only. It never changes backend
 * data, sensor readings, anomalies, forecasts, recommendations, permissions,
 * Demo Mode, the simulator, IoT mode or enabled modules. The same data set is
 * always rendered; only its composition/layout differs.
 *
 * This module is intentionally free of React so it can be unit tested directly.
 */

export const DASHBOARD_STYLE_VALUES = [
  "EXECUTIVE",
  "OPERATIONS",
  "ANALYTICS",
  "COMMAND_CENTER",
] as const;

export type DashboardStyle = (typeof DASHBOARD_STYLE_VALUES)[number];

export const DEFAULT_DASHBOARD_STYLE: DashboardStyle = "EXECUTIVE";

/**
 * Light formatting variants accepted on the client, mirroring the backend
 * normaliser: case, spaces and dashes. Unknown values are never invented.
 */
const STYLE_ALIASES: Record<string, DashboardStyle> = {
  EXECUTIVE: "EXECUTIVE",
  OPERATIONS: "OPERATIONS",
  ANALYTICS: "ANALYTICS",
  COMMAND_CENTER: "COMMAND_CENTER",
};

export function isDashboardStyle(value: unknown): value is DashboardStyle {
  return typeof value === "string" && (DASHBOARD_STYLE_VALUES as readonly string[]).includes(value);
}

export function normaliseDashboardStyle(value: unknown): DashboardStyle {
  if (typeof value !== "string") return DEFAULT_DASHBOARD_STYLE;
  const canonical = value.trim().toUpperCase().replace(/[\s\-]+/g, "_");
  return STYLE_ALIASES[canonical] ?? DEFAULT_DASHBOARD_STYLE;
}

/** Local per-organisation paint cache key. Server remains the source of truth. */
export function dashboardStyleStorageKey(organisationId: string): string {
  return `greennexa_dashboard_style:${organisationId}`;
}

/** Minimal storage shape so the cache can be unit tested without a DOM. */
export interface StyleStorageLike {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
}

/** Read the cached style for one organisation (null when nothing is cached). */
export function readCachedDashboardStyle(
  storage: StyleStorageLike | null | undefined,
  organisationId: string | null | undefined
): DashboardStyle | null {
  if (!storage || !organisationId) return null;
  try {
    const raw = storage.getItem(dashboardStyleStorageKey(organisationId));
    return raw ? normaliseDashboardStyle(raw) : null;
  } catch {
    return null;
  }
}

/** Cache the style for one organisation only. */
export function cacheDashboardStyle(
  storage: StyleStorageLike | null | undefined,
  organisationId: string | null | undefined,
  style: DashboardStyle
): void {
  if (!storage || !organisationId) return;
  try {
    storage.setItem(dashboardStyleStorageKey(organisationId), style);
  } catch {
    /* storage unavailable — the server value still wins */
  }
}

/* ------------------------------------------------------------------------- */
/* Sections                                                                  */
/* ------------------------------------------------------------------------- */

export type DashboardSection =
  | "health-summary"
  | "kpis"
  | "critical-alerts"
  | "insights"
  | "forecast"
  | "anomalies"
  | "recommendations"
  | "quick-actions"
  | "recent-activity"
  | "analytics-metrics"
  | "analytics-trend"
  | "modules"
  | "ward-status"
  | "spatial-overview"
  | "associated-orgs";

/** What data actually exists for the organisation being viewed. */
export interface DashboardCapabilities {
  hasKpis: boolean;
  hasAnomalies: boolean;
  hasRecommendations: boolean;
  hasForecast: boolean;
  hasTrend: boolean;
  hasRecentReadings: boolean;
  hasWards: boolean;
  hasModules: boolean;
  hasAssociatedOrgs: boolean;
  isMunicipality: boolean;
}

export type KpiEmphasis = "hero" | "dense" | "table" | "radial";
export type PanelVariant = "summary" | "priority" | "trend" | "critical" | "table" | "actions";

export interface PreviewCell {
  /** Column span of the miniature layout thumbnail. */
  span: number;
  /** Visual weight of the miniature cell. */
  tone: "surface" | "accent" | "alert" | "muted";
}

export interface DashboardStyleDefinition {
  id: DashboardStyle;
  label: string;
  tagline: string;
  description: string;
  audience: string;
  /** Ordered composition of the dashboard for this style. */
  sections: DashboardSection[];
  /** Section rendered as the full-width leading element. */
  leadSection: DashboardSection;
  grid: { columns: string; gap: number };
  kpi: { emphasis: KpiEmphasis; minCardWidth: number; maxCards: number | null };
  variants: Partial<Record<DashboardSection, PanelVariant>>;
  preview: { columns: number; cells: PreviewCell[] };
}

export const DASHBOARD_STYLES: DashboardStyleDefinition[] = [
  {
    id: "EXECUTIVE",
    label: "Executive",
    tagline: "Understand the situation quickly",
    description:
      "Large KPI cards, overall performance summary, critical alerts, AI insights and forecast. High-level information first, minimal operational clutter.",
    audience: "Management / senior decision-makers",
    sections: [
      "health-summary",
      "kpis",
      "critical-alerts",
      "insights",
      "forecast",
      "anomalies",
      "recommendations",
      "recent-activity",
      "modules",
      "ward-status",
      "quick-actions",
      "spatial-overview",
      "associated-orgs",
      "analytics-metrics",
      "analytics-trend",
    ],
    leadSection: "health-summary",
    grid: { columns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24 },
    kpi: { emphasis: "hero", minCardWidth: 300, maxCards: 4 },
    variants: { anomalies: "critical", recommendations: "summary" },
    preview: {
      columns: 4,
      cells: [
        { span: 4, tone: "accent" },
        { span: 1, tone: "surface" },
        { span: 1, tone: "surface" },
        { span: 1, tone: "surface" },
        { span: 1, tone: "surface" },
        { span: 2, tone: "muted" },
        { span: 2, tone: "muted" },
      ],
    },
  },
  {
    id: "OPERATIONS",
    label: "Operations",
    tagline: "Show me what needs attention now",
    description:
      "Live status, current values, active anomalies, priority issues, maintenance/action panels, operational alerts and quick actions.",
    audience: "Operators / facility staff",
    sections: [
      "quick-actions",
      "health-summary",
      "kpis",
      "anomalies",
      "critical-alerts",
      "recommendations",
      "modules",
      "recent-activity",
      "ward-status",
      "forecast",
      "insights",
      "spatial-overview",
      "associated-orgs",
      "analytics-metrics",
      "analytics-trend",
    ],
    leadSection: "quick-actions",
    grid: { columns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 },
    kpi: { emphasis: "dense", minCardWidth: 200, maxCards: 8 },
    variants: { anomalies: "priority", recommendations: "actions" },
    preview: {
      columns: 4,
      cells: [
        { span: 1, tone: "surface" },
        { span: 1, tone: "alert" },
        { span: 1, tone: "alert" },
        { span: 1, tone: "surface" },
        { span: 2, tone: "accent" },
        { span: 2, tone: "surface" },
        { span: 2, tone: "muted" },
        { span: 2, tone: "muted" },
      ],
    },
  },
  {
    id: "ANALYTICS",
    label: "Analytics",
    tagline: "Analyse the data deeply",
    description:
      "Chart-heavy layout: historical trends, comparisons, forecast panels, anomaly trends, metric filters, detailed metric tables.",
    audience: "Data analysis / sustainability / technical users",
    sections: [
      "analytics-metrics",
      "analytics-trend",
      "forecast",
      "health-summary",
      "kpis",
      "anomalies",
      "recommendations",
      "insights",
      "recent-activity",
      "modules",
      "ward-status",
      "critical-alerts",
      "quick-actions",
      "spatial-overview",
      "associated-orgs",
    ],
    leadSection: "analytics-metrics",
    grid: { columns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 20 },
    kpi: { emphasis: "table", minCardWidth: 180, maxCards: null },
    variants: { anomalies: "trend", recommendations: "table" },
    preview: {
      columns: 4,
      cells: [
        { span: 2, tone: "muted" },
        { span: 2, tone: "muted" },
        { span: 2, tone: "accent" },
        { span: 2, tone: "surface" },
        { span: 4, tone: "muted" },
      ],
    },
  },
  {
    id: "COMMAND_CENTER",
    label: "Command Center",
    tagline: "Monitor the whole operation from one place",
    description:
      "Large central operational view with spatial/ward status, critical alerts, quick actions, AI insight, forecast and live operational indicators.",
    audience: "Mission control / municipality / large operational monitoring",
    sections: [
      "spatial-overview",
      "kpis",
      "critical-alerts",
      "ward-status",
      "quick-actions",
      "health-summary",
      "insights",
      "forecast",
      "anomalies",
      "recommendations",
      "recent-activity",
      "modules",
      "associated-orgs",
      "analytics-metrics",
      "analytics-trend",
    ],
    leadSection: "spatial-overview",
    grid: { columns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 18 },
    kpi: { emphasis: "radial", minCardWidth: 170, maxCards: 6 },
    variants: { anomalies: "critical" },
    preview: {
      columns: 4,
      cells: [
        { span: 1, tone: "muted" },
        { span: 2, tone: "accent" },
        { span: 1, tone: "muted" },
        { span: 1, tone: "alert" },
        { span: 2, tone: "surface" },
        { span: 1, tone: "alert" },
        { span: 1, tone: "surface" },
        { span: 1, tone: "surface" },
        { span: 1, tone: "surface" },
      ],
    },
  },
];

export function getStyleDefinition(style: unknown): DashboardStyleDefinition {
  const id = normaliseDashboardStyle(style);
  return (
    DASHBOARD_STYLES.find((definition) => definition.id === id) ??
    DASHBOARD_STYLES.find((definition) => definition.id === DEFAULT_DASHBOARD_STYLE)!
  );
}

/**
 * Capability → section requirement. Every requirement in a list must hold.
 * `[]` means the section is always safe to render (pure navigation chrome).
 * Sections without data are never fabricated.
 */
const SECTION_REQUIRES: Record<DashboardSection, (keyof DashboardCapabilities)[]> = {
  "health-summary": ["hasKpis"],
  kpis: ["hasKpis"],
  "critical-alerts": ["hasAnomalies"],
  insights: ["hasRecommendations"],
  forecast: ["hasForecast"],
  anomalies: ["hasAnomalies"],
  recommendations: ["hasRecommendations"],
  "quick-actions": [],
  "recent-activity": ["hasRecentReadings"],
  "analytics-metrics": ["hasKpis"],
  "analytics-trend": ["hasTrend"],
  modules: ["hasModules"],
  "ward-status": ["isMunicipality", "hasWards"],
  "spatial-overview": ["hasModules"],
  "associated-orgs": ["isMunicipality", "hasAssociatedOrgs"],
};

/**
 * Resolve the ordered, renderable sections for a style.
 * Every style can render every panel; each style merely prioritises them
 * differently. Sections whose data does not exist are dropped, so a style can
 * never fabricate a module.
 */
export function resolveSections(
  style: unknown,
  capabilities: DashboardCapabilities
): DashboardSection[] {
  const definition = getStyleDefinition(style);
  return definition.sections.filter((section) =>
    SECTION_REQUIRES[section].every((capability) => Boolean(capabilities[capability]))
  );
}

/**
 * Pack the ordered sections into layout rows for a style.
 * Sections listed in `shareRow` sit side by side, `groupSize` per row; anything
 * else occupies a full-width row. This is what makes two styles render the same
 * panels in visibly different compositions.
 */
export function composeRows(
  sections: DashboardSection[],
  options: { shareRow: DashboardSection[]; groupSize?: 1 | 2 | 3 }
): DashboardSection[][] {
  const groupSize = Math.max(1, Math.min(3, options.groupSize ?? 2));
  const shareable = new Set(options.shareRow);
  const rows: DashboardSection[][] = [];
  let current: DashboardSection[] = [];

  const flush = () => {
    if (current.length > 0) rows.push(current);
    current = [];
  };

  for (const section of sections) {
    if (!shareable.has(section)) {
      flush();
      rows.push([section]);
      continue;
    }
    current.push(section);
    if (current.length >= groupSize) flush();
  }
  flush();
  return rows;
}

/** Section → panel variant for the current style. */
export function getSectionVariant(
  style: unknown,
  section: DashboardSection
): PanelVariant {
  return getStyleDefinition(style).variants[section] ?? "summary";
}

/** KPI emphasis for the current style. */
export function getKpiEmphasis(style: unknown): KpiEmphasis {
  return getStyleDefinition(style).kpi.emphasis;
}
