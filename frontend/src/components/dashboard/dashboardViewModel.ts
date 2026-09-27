/**
 * GreenNexa — Dashboard View Model (shared by every dashboard style).
 *
 * A single normalised view model is built once from the backend payloads and is
 * then rendered by whichever dashboard style is selected. Building the view model
 * never writes, resets or refetches anything: it is a pure transformation of data
 * that already exists, which is what guarantees that switching style only changes
 * presentation.
 *
 * This module is intentionally free of imports so it can be unit tested directly.
 */

/* Structural capabilities of the data that actually exists for this organisation. */
export interface DashboardDataCapabilities {
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

export type OperationalStatus = "normal" | "warning" | "critical" | "nodata";

export interface KpiEntry {
  key: string;
  title: string;
  value: number | null;
  displayValue: string;
  unit: string;
  average: number | null;
  minimum: number | null;
  maximum: number | null;
  readingCount: number;
  trendPct: number | null;
  status: OperationalStatus;
  isAnomaly: boolean;
  href: string;
}

export interface AnomalyEntry {
  id: string;
  metric: string;
  label: string;
  severity: string;
  status: string;
  value: number | null;
  unit: string;
  expectedMin: number | null;
  expectedMax: number | null;
  timestamp: string | null;
  reason: string;
  location: string;
  rank: number;
}

export interface RecommendationEntry {
  id: string;
  metric: string;
  title: string;
  description: string;
  actions: string[];
  priority: string;
  severity: string;
  createdAt: string | null;
}

export interface ReadingEntry {
  id: string;
  sensorType: string;
  value: number | null;
  unit: string;
  source: string;
  timestamp: string | null;
  isAnomaly: boolean;
}

export interface ModuleEntry {
  id: string;
  label: string;
  icon: string;
  color: string;
  background: string;
  href: string;
  status: OperationalStatus;
  hasData: boolean;
  displayValue: string;
  unit: string;
  trendLabel: string;
  anomaliesCount: number;
}

export interface WardEntry {
  id: string;
  wardNumber: string;
  wardName: string;
  zone: string;
  population: number | null;
  areaSqKm: number | null;
  status: OperationalStatus;
  alertsCount: number;
  href: string;
  hasUnread: boolean;
}

export interface ForecastPointEntry {
  label: string;
  value: number;
  unit: string;
  timestamp: string | null;
}

export interface TrendSeriesPoint {
  timestamp: number;
  value: number;
  isAnomaly: boolean;
}

export interface AssociatedOrgEntry {
  id: string;
  name: string;
  orgType: string;
  location: string;
}

export interface QuickActionEntry {
  id: string;
  label: string;
  href: string;
  tone: "primary" | "warning" | "neutral";
}

export interface ScoreEntry {
  value: number;
  label: string;
  color: string;
}

export interface DashboardViewModel {
  scope: "facility" | "municipality";
  organisationId: string;
  organisationName: string;
  orgType: string;
  facilityName: string;
  dataSource: string;
  lastUpdatedAt: string | null;
  isMunicipality: boolean;
  loading: boolean;
  score: ScoreEntry;
  activeAnomalyCount: number;
  criticalAnomalyCount: number;
  totalWards: number;
  kpis: KpiEntry[];
  anomalies: AnomalyEntry[];
  recommendations: RecommendationEntry[];
  recentReadings: ReadingEntry[];
  modules: ModuleEntry[];
  wards: WardEntry[];
  associatedOrgs: AssociatedOrgEntry[];
  forecast: { metric: string; unit: string; available: boolean; message: string; points: ForecastPointEntry[] };
  trend: { metric: string; unit: string; available: boolean; points: TrendSeriesPoint[] };
  quickActions: QuickActionEntry[];
  capabilities: DashboardDataCapabilities;
}

/* ------------------------------------------------------------------------- */
/* Raw input                                                                 */
/* ------------------------------------------------------------------------- */

export interface DashboardViewModelInput {
  scope?: "facility" | "municipality";
  organisationId: string;
  organisationName?: string;
  orgType?: string;
  facilityName?: string;
  dataSource?: string;
  lastUpdatedAt?: string | null;
  isMunicipality?: boolean;
  loading?: boolean;
  score?: ScoreEntry;
  kpis?: Record<string, any> | null;
  legacyMetrics?: Record<string, any> | null;
  anomalies?: any[] | null;
  recommendations?: any[] | null;
  recentReadings?: any[] | null;
  modules?: ModuleEntry[] | null;
  wards?: any[] | null;
  associatedOrgs?: any[] | null;
  forecast?: { metric?: string; unit?: string; available?: boolean; message?: string; points?: any[] } | null;
  trend?: { metric?: string; unit?: string; available?: boolean; points?: any[] } | null;
  activeAnomalyCount?: number;
  criticalAnomalyCount?: number;
  isWardUnread?: (wardId: string, wardNumber: string) => boolean;
}

const SEVERITY_RANK: Record<string, number> = {
  CRITICAL: 4,
  HIGH: 3,
  MEDIUM: 2,
  LOW: 1,
  NORMAL: 0,
};

const METRIC_TITLES: Record<string, string> = {
  energy: "Energy Consumption",
  water: "Water Usage",
  waste: "Waste Generation",
  temperature: "Indoor Temperature",
  climate: "Climate",
  humidity: "Humidity",
  co2: "CO2 Concentration",
  air_quality: "Air Quality",
  assets: "Assets Monitoring",
  equipment_asset: "Municipal Assets",
  safety: "Safety",
  traffic: "Traffic Management",
  parking: "Parking Occupancy",
  water_flow: "Water Flow",
  water_level: "Water Level",
  sewage: "Sewage & Drainage",
  sewage_level: "Sewage Level",
  rainfall: "Rainfall",
  street_lighting: "Street Lighting",
  roads: "Roads & Infrastructure",
  parks: "Parks & Public Spaces",
  occupancy: "Occupancy",
  vibration: "Vibration",
  pressure: "Pressure",
  flow: "Flow",
  current_voltage: "Current & Voltage",
  rpm: "RPM",
  machine_temperature: "Machine Temperature",
  runtime_hours: "Runtime Hours",
  acoustic_sound: "Acoustic Sound",
  gas: "Gas Level",
  dust_pm: "Dust / PM",
  fire_smoke: "Fire & Smoke",
  oil_fluid_level: "Oil / Fluid Level",
};

const ACTIVE_ANOMALY_STATUSES = ["OPEN", "ACKNOWLEDGED", "ACTIVE"];
const ACTIVE_RECOMMENDATION_STATUSES = ["OPEN", "ACTIVE"];

export function metricTitle(key: string): string {
  const clean = (key || "").trim().toLowerCase();
  if (METRIC_TITLES[clean]) return METRIC_TITLES[clean];
  return clean.charAt(0).toUpperCase() + clean.slice(1);
}

export function severityRank(severity: unknown): number {
  return SEVERITY_RANK[String(severity || "").toUpperCase()] ?? 0;
}

export function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function formatValue(value: number | null, fractionDigits = 1): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString(undefined, { maximumFractionDigits: fractionDigits });
}

function statusFromSeverity(severity: unknown, isAnomaly?: boolean): OperationalStatus {
  const sev = String(severity || "").toUpperCase();
  if (sev === "CRITICAL") return "critical";
  if (sev === "HIGH" || sev === "MEDIUM") return "warning";
  if (isAnomaly) return "warning";
  return "normal";
}

function asArray<T = any>(value: unknown): T[] {
  if (Array.isArray(value)) return value as T[];
  if (value && typeof value === "object" && Array.isArray((value as any).items)) {
    return (value as any).items as T[];
  }
  return [];
}

/* ------------------------------------------------------------------------- */
/* Normalisers                                                               */
/* ------------------------------------------------------------------------- */

export function normaliseKpis(
  kpis?: Record<string, any> | null,
  legacy?: Record<string, any> | null,
  options?: { orgId?: string }
): KpiEntry[] {
  const entries: KpiEntry[] = [];
  const source = kpis && Object.keys(kpis).length > 0 ? kpis : null;
  const orgSuffix = options?.orgId ? `?org=${encodeURIComponent(options.orgId)}` : "";

  if (source) {
    Object.entries(source).forEach(([key, data]) => {
      const cleanKey = String(key).trim().toLowerCase();
      const value = toNumber(data?.latest_value ?? data?.current ?? data?.average);
      const average = toNumber(data?.average);
      const trendPct = value != null && average != null && average !== 0 ? ((value - average) / average) * 100 : null;
      entries.push({
        key: cleanKey,
        title: metricTitle(cleanKey),
        value,
        displayValue: formatValue(value),
        unit: String(data?.unit ?? ""),
        average,
        minimum: toNumber(data?.minimum),
        maximum: toNumber(data?.maximum),
        readingCount: Number(data?.reading_count ?? 0),
        trendPct,
        status: statusFromSeverity(data?.anomaly_severity, data?.is_anomaly),
        isAnomaly: Boolean(data?.is_anomaly),
        href: `/dashboard/modules/${cleanKey}${orgSuffix}`,
      });
    });
    return entries;
  }

  if (legacy) {
    Object.entries(legacy).forEach(([key, data]) => {
      const cleanKey = String(key).trim().toLowerCase();
      const value = toNumber((data as any)?.current);
      entries.push({
        key: cleanKey,
        title: metricTitle(cleanKey),
        value,
        displayValue: formatValue(value),
        unit: String((data as any)?.unit ?? ""),
        average: null,
        minimum: null,
        maximum: null,
        readingCount: 0,
        trendPct: toNumber((data as any)?.trend_pct),
        status: "normal",
        isAnomaly: false,
        href: `/dashboard/modules/${cleanKey}${orgSuffix}`,
      });
    });
  }
  return entries;
}

export function normaliseAnomalies(list: unknown): AnomalyEntry[] {
  return asArray<any>(list)
    .map((raw) => {
      const metric = String(raw?.metric || raw?.sensor_type || "sensor").trim().toLowerCase();
      const severity = String(raw?.severity || "NORMAL").toUpperCase();
      const value = toNumber(raw?.value);
      return {
        id: String(raw?.id ?? ""),
        metric,
        label: metricTitle(metric),
        severity,
        status: String(raw?.status ?? "OPEN").toUpperCase(),
        value,
        unit: String(raw?.unit ?? ""),
        expectedMin: toNumber(raw?.expected_min),
        expectedMax: toNumber(raw?.expected_max),
        timestamp: raw?.timestamp ?? null,
        reason: String(raw?.reason || raw?.description || ""),
        location: String(raw?.ward_id || raw?.block_id || raw?.facility_id || ""),
        rank: severityRank(severity),
      } satisfies AnomalyEntry;
    })
    .sort((a, b) => b.rank - a.rank);
}

export function normaliseRecommendations(list: unknown): RecommendationEntry[] {
  return asArray<any>(list)
    .filter((raw) => {
      const status = String(raw?.status ?? "ACTIVE").toUpperCase();
      return ACTIVE_RECOMMENDATION_STATUSES.includes(status);
    })
    .map((raw) => {
      const metric = String(raw?.metric || raw?.sensor_type || "").trim().toLowerCase();
      const actions = Array.isArray(raw?.recommended_actions)
        ? raw.recommended_actions.filter(Boolean)
        : Array.isArray(raw?.recommended_actions_list)
        ? raw.recommended_actions_list.filter(Boolean)
        : [];
      const summary = String(raw?.summary || raw?.title || raw?.recommendation || "AI optimisation action");
      return {
        id: String(raw?.id ?? ""),
        metric,
        title: metric ? `${metricTitle(metric)} — ${summary}` : summary,
        description: String(raw?.explanation || raw?.confidence_note || summary),
        actions: actions.length > 0 ? actions : [String(raw?.suggested_action || "Investigate the affected asset and verify the reading.")],
        priority: String(raw?.priority || "LOW").toUpperCase(),
        severity: String(raw?.severity || "NORMAL").toUpperCase(),
        createdAt: raw?.created_at ?? null,
      } satisfies RecommendationEntry;
    })
    .sort((a, b) => severityRank(b.priority) - severityRank(a.priority));
}

export function normaliseReadings(list: unknown): ReadingEntry[] {
  return asArray<any>(list).map((raw) => ({
    id: String(raw?.id ?? ""),
    sensorType: String(raw?.sensor_type ?? "").trim().toLowerCase(),
    value: toNumber(raw?.value),
    unit: String(raw?.unit ?? ""),
    source: String(raw?.source ?? ""),
    timestamp: raw?.timestamp ?? null,
    isAnomaly: Boolean(raw?.is_anomaly),
  }));
}

export function normaliseWards(
  list: unknown,
  options: {
    anomalies?: AnomalyEntry[];
    isWardUnread?: (wardId: string, wardNumber: string) => boolean;
    orgId?: string;
  } = {}
): WardEntry[] {
  const anomalies = options.anomalies ?? [];
  const orgSuffix = options.orgId ? `?org=${encodeURIComponent(options.orgId)}` : "";
  return asArray<any>(list).map((raw) => {
    const wardId = String(raw?.id ?? "");
    const wardNumber = String(raw?.ward_number ?? "");
    const name = String(raw?.ward_name ?? `Ward ${wardNumber}`);
    const wardAnomalies = anomalies.filter(
      (a) => (a.location && (a.location === wardId || a.location === wardNumber || a.location === name)) || false
    );
    const critical = wardAnomalies.some((a) => a.severity === "CRITICAL");
    const status: OperationalStatus = critical ? "critical" : wardAnomalies.length > 0 ? "warning" : "normal";
    return {
      id: wardId,
      wardNumber,
      wardName: name,
      zone: String(raw?.zone ?? ""),
      population: toNumber(raw?.population),
      areaSqKm: toNumber(raw?.area_sq_km),
      status,
      alertsCount: wardAnomalies.length,
      href: `/dashboard/wards/${wardId}${orgSuffix}`,
      hasUnread: Boolean(options.isWardUnread?.(wardId, wardNumber)),
    } satisfies WardEntry;
  });
}

export function normaliseAssociatedOrgs(list: unknown): AssociatedOrgEntry[] {
  return asArray<any>(list).map((raw) => ({
    id: String(raw?.id ?? ""),
    name: String(raw?.name ?? ""),
    orgType: String(raw?.org_type ?? ""),
    location: String(raw?.location ?? [raw?.city, raw?.state].filter(Boolean).join(", ")),
  }));
}

export function normaliseForecast(input?: DashboardViewModelInput["forecast"]) {
  const points = asArray<any>(input?.points).map((p) => {
    const value = toNumber(p?.predicted_value ?? p?.value) ?? 0;
    return {
      label: p?.timestamp ? new Date(p.timestamp).toLocaleString(undefined, { hour: "2-digit", minute: "2-digit" }) : "—",
      value,
      unit: String(input?.unit ?? ""),
      timestamp: p?.timestamp ?? null,
    } satisfies ForecastPointEntry;
  });
  return {
    metric: String(input?.metric ?? ""),
    unit: String(input?.unit ?? ""),
    available: Boolean(input?.available) && points.length > 0,
    message: String(input?.message ?? "Forecast is generated once enough history is available for this metric."),
    points,
  };
}

export function normaliseTrend(input?: DashboardViewModelInput["trend"]) {
  const points = asArray<any>(input?.points)
    .map((p) => ({
      timestamp: p?.timestamp ? new Date(p.timestamp).getTime() : NaN,
      value: toNumber(p?.value) ?? 0,
      isAnomaly: Boolean(p?.is_anomaly),
    }))
    .filter((p) => Number.isFinite(p.timestamp))
    .sort((a, b) => a.timestamp - b.timestamp);
  return {
    metric: String(input?.metric ?? ""),
    unit: String(input?.unit ?? ""),
    available: points.length > 1,
    points,
  };
}

/**
 * Deterministically pick the single metric used for the trend and forecast
 * panels. Every style uses the same metric, so switching style never changes
 * which series is displayed.
 */
const METRIC_PREFERENCE = ["energy", "water", "waste", "temperature", "air_quality", "climate", "occupancy"];

export function pickAnalyticsMetric(availableKeys: string[]): string | null {
  const keys = (availableKeys || []).map((k) => String(k).trim().toLowerCase()).filter(Boolean);
  if (keys.length === 0) return null;
  for (const preferred of METRIC_PREFERENCE) {
    if (keys.includes(preferred)) return preferred;
  }
  return keys[0];
}

export function buildQuickActions(vm: {
  isMunicipality: boolean;
  organisationId: string;
  anomalyCount: number;
  hasWards: boolean;
}): QuickActionEntry[] {
  const actions: QuickActionEntry[] = [];
  const orgSuffix = vm.organisationId ? `?org=${encodeURIComponent(vm.organisationId)}` : "";
  if (vm.isMunicipality && vm.hasWards) {
    actions.push({ id: "wards", label: "Ward operations", href: `/municipality/associated-orgs${orgSuffix}`, tone: "primary" });
  }
  actions.push({
    id: "anomalies",
    label: vm.anomalyCount > 0 ? `Triage ${vm.anomalyCount} active anomal${vm.anomalyCount === 1 ? "y" : "ies"}` : "Review anomaly queue",
    href: `/anomalies${orgSuffix}`,
    tone: vm.anomalyCount > 0 ? "warning" : "neutral",
  });
  actions.push({ id: "recommendations", label: "AI action plans", href: `/recommendations${orgSuffix}`, tone: "primary" });
  actions.push({ id: "forecast", label: "Forecast centre", href: `/forecast${orgSuffix}`, tone: "neutral" });
  actions.push({ id: "reports", label: "Reports", href: `/reports${orgSuffix}`, tone: "neutral" });
  return actions;
}

/* ------------------------------------------------------------------------- */
/* Builder                                                                   */
/* ------------------------------------------------------------------------- */

export function buildDashboardViewModel(input: DashboardViewModelInput): DashboardViewModel {
  const isMunicipality = Boolean(input.isMunicipality);
  const orgId = input.organisationId;
  const kpis = normaliseKpis(input.kpis, input.legacyMetrics, { orgId });
  const anomalies = normaliseAnomalies(input.anomalies);
  const recommendations = normaliseRecommendations(input.recommendations);
  const recentReadings = normaliseReadings(input.recentReadings);
  const orgSuffix = orgId ? `?org=${encodeURIComponent(orgId)}` : "";
  const modules = (input.modules ?? []).map((m) => ({
    ...m,
    href: m.href && !m.href.includes("?org=") ? `${m.href}${orgSuffix}` : m.href,
  }));
  const wards = normaliseWards(input.wards, {
    anomalies,
    isWardUnread: input.isWardUnread,
    orgId,
  });
  const associatedOrgs = normaliseAssociatedOrgs(input.associatedOrgs);
  const forecast = normaliseForecast(input.forecast);
  const trend = normaliseTrend(input.trend);

  const activeAnomalies = anomalies.filter((a) => ACTIVE_ANOMALY_STATUSES.includes(a.status));
  const activeAnomalyCount = input.activeAnomalyCount ?? activeAnomalies.length;
  const criticalAnomalyCount =
    input.criticalAnomalyCount ?? anomalies.filter((a) => a.severity === "CRITICAL" || a.severity === "HIGH").length;

  const capabilities: DashboardDataCapabilities = {
    hasKpis: kpis.length > 0,
    hasAnomalies: anomalies.length > 0,
    hasRecommendations: recommendations.length > 0,
    hasForecast: forecast.available,
    hasTrend: trend.available,
    hasRecentReadings: recentReadings.length > 0,
    hasWards: wards.length > 0,
    hasModules: modules.length > 0,
    hasAssociatedOrgs: associatedOrgs.length > 0,
    isMunicipality,
  };

  return {
    scope: input.scope ?? (isMunicipality ? "municipality" : "facility"),
    organisationId: input.organisationId,
    organisationName: input.organisationName || input.organisationId,
    orgType: String(input.orgType ?? ""),
    facilityName: String(input.facilityName ?? ""),
    dataSource: String(input.dataSource ?? "synthetic"),
    lastUpdatedAt: input.lastUpdatedAt ?? null,
    isMunicipality,
    loading: Boolean(input.loading),
    score: input.score ?? { value: 100, label: "OPTIMAL", color: "#22c55e" },
    activeAnomalyCount,
    criticalAnomalyCount,
    totalWards: wards.length,
    kpis,
    anomalies,
    recommendations,
    recentReadings,
    modules,
    wards,
    associatedOrgs,
    forecast,
    trend,
    quickActions: buildQuickActions({
      isMunicipality,
      organisationId: input.organisationId,
      anomalyCount: activeAnomalyCount,
      hasWards: wards.length > 0,
    }),
    capabilities,
  };
}
