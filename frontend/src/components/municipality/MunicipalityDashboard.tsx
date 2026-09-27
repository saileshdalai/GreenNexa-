"use client";

import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { AnomalyRecord, AIRecommendation, AnomalyListResponse, RecommendationListResponse } from "@/types";
import { DataSourceBadge } from "@/components/ui/DataSourceBadge";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { Building2, RefreshCw } from "lucide-react";
import { MunicipalityOrgOverview } from "@/components/municipality/MunicipalityOrgOverview";
import { useNotifications } from "@/context/NotificationContext";
import { useDashboardStyle } from "@/context/DashboardStyleContext";
import { DashboardRenderer } from "@/components/dashboard/DashboardRenderer";
import { buildDashboardViewModel, DashboardViewModelInput, ModuleEntry } from "@/components/dashboard/dashboardViewModel";
import { useDashboardExtras } from "@/components/dashboard/useDashboardExtras";
import { calculateOptimalScore, getOptimalScoreColorAndLabel } from "@/lib/scoring";

interface MunicipalityDashboardProps {
  orgId: string;
  orgName?: string;
}

interface AssociatedOrg {
  id: string;
  name: string;
  org_type: string;
  city?: string;
  state?: string;
}

interface MunicipalityWardItem {
  id: string;
  ward_number: string;
  ward_name: string;
  zone?: string;
  population?: number;
  area_sq_km?: number;
  is_active?: boolean;
}

interface DashboardKPIs {
  organisation_name?: string;
  active_anomaly_count?: number;
  critical_anomaly_count?: number;
  data_source?: string;
  optimal_score?: number;
  org_type?: string;
  wards?: MunicipalityWardItem[];
  total_wards?: number;
  last_updated_at?: string;
  kpis?: Record<string, {
    sensor_type: string;
    unit?: string;
    latest_value?: number;
    average?: number;
    minimum?: number;
    maximum?: number;
    reading_count?: number;
    is_anomaly?: boolean;
    anomaly_severity?: string;
  }>;
}

const CIVIC_MODULES = [
  { id: "water", label: "Water Supply", color: "#38bdf8", bg: "rgba(56,189,248,0.1)", icon: "💧" },
  { id: "waste", label: "Waste Management", color: "#10b981", bg: "rgba(16,185,129,0.1)", icon: "🗑️" },
  { id: "sewage", label: "Sewage & Drainage", color: "#0ea5e9", bg: "rgba(14,165,233,0.1)", icon: "🚰" },
  { id: "roads", label: "Roads & Infrastructure", color: "#f97316", bg: "rgba(249,115,22,0.1)", icon: "🛣️" },
  { id: "traffic", label: "Traffic & Parking", color: "#fb923c", bg: "rgba(251,146,60,0.1)", icon: "🚗" },
  { id: "street_lighting", label: "Street Lighting", color: "#f59e0b", bg: "rgba(245,158,11,0.1)", icon: "💡" },
  { id: "parks", label: "Parks & Public Spaces", color: "#22c55e", bg: "rgba(34,197,94,0.1)", icon: "🌳" },
  { id: "air_quality", label: "Air Quality", color: "#a78bfa", bg: "rgba(167,139,250,0.1)", icon: "🌡️" },
  { id: "climate", label: "Climate & Environment", color: "#34d399", bg: "rgba(52,211,153,0.1)", icon: "🌱" },
  { id: "equipment_asset", label: "Municipal Assets", color: "#6366f1", bg: "rgba(99,102,241,0.1)", icon: "🏢" },
  { id: "safety", label: "Safety & Incidents", color: "#ef4444", bg: "rgba(239,68,68,0.1)", icon: "🚨" },
];

const MODULE_METRICS: Record<string, { primary: string; fallback?: string }> = {
  "Water Supply": { primary: "water", fallback: "water_flow" },
  "Waste Management": { primary: "waste" },
  "Sewage & Drainage": { primary: "sewage", fallback: "sewage_level" },
  "Roads & Infrastructure": { primary: "roads", fallback: "traffic" },
  "Traffic & Parking": { primary: "traffic", fallback: "parking" },
  "Street Lighting": { primary: "street_lighting", fallback: "energy" },
  "Parks & Public Spaces": { primary: "parks", fallback: "rainfall" },
  "Air Quality": { primary: "air_quality" },
  "Climate & Environment": { primary: "climate", fallback: "temperature" },
  "Municipal Assets": { primary: "equipment_asset", fallback: "assets" },
  "Safety & Incidents": { primary: "safety" },
};

export const MunicipalityDashboard: React.FC<MunicipalityDashboardProps> = ({ orgId, orgName }) => {
  const { isWardUnread } = useNotifications();
  const { style, definition } = useDashboardStyle();
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [associatedOrgs, setAssociatedOrgs] = useState<AssociatedOrg[]>([]);
  const [selectedOrgForView, setSelectedOrgForView] = useState<{ id: string; name: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [secondsAgo, setSecondsAgo] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const loadData = async () => {
    setLoading(true);
    try {
      const [kpiRes, anomalyRes, recRes, assocRes] = await Promise.allSettled([
        api.get<DashboardKPIs>(`/api/v1/dashboard/${orgId}`),
        api.get<AnomalyListResponse | AnomalyRecord[]>(`/api/v1/anomalies`, { organisation_id: orgId, limit: 6, status: "OPEN" }),
        api.get<RecommendationListResponse | AIRecommendation[]>(`/api/v1/recommendations`, { organisation_id: orgId, status: "OPEN" }),
        api.get<{ associated_orgs?: AssociatedOrg[] } | AssociatedOrg[]>(`/api/v1/organisations/${orgId}/associated-government-orgs`),
      ]);

      if (kpiRes.status === "fulfilled") {
        setKpis(kpiRes.value);
        if (kpiRes.value?.last_updated_at) {
          setLastUpdated(new Date(kpiRes.value.last_updated_at));
        }
      }

      if (anomalyRes.status === "fulfilled" && anomalyRes.value) {
        const val = anomalyRes.value;
        const list = Array.isArray(val) ? val : Array.isArray((val as AnomalyListResponse)?.items) ? (val as AnomalyListResponse).items : [];
        setAnomalies(list);
      }

      if (recRes.status === "fulfilled" && recRes.value) {
        const val = recRes.value;
        const list = Array.isArray(val) ? val : Array.isArray((val as RecommendationListResponse)?.items) ? (val as RecommendationListResponse).items : [];
        setRecommendations(list.filter((r: AIRecommendation) => r.status === "OPEN" || r.status === "ACTIVE").slice(0, 4));
      }

      if (assocRes.status === "fulfilled" && assocRes.value) {
        const val = assocRes.value;
        const list: AssociatedOrg[] = Array.isArray(val)
          ? val
          : (val as any)?.associated_government_orgs || (val as any)?.associated_orgs || [];
        setAssociatedOrgs(list);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!orgId) return;
    loadData();
    const poll = setInterval(loadData, 30000);
    const sync = () => loadData();
    window.addEventListener("greennexa_demo_mode_changed", sync);
    window.addEventListener("greennexa_telemetry_updated", sync);
    window.addEventListener("greennexa_day_changed", sync);
    return () => {
      clearInterval(poll);
      window.removeEventListener("greennexa_demo_mode_changed", sync);
      window.removeEventListener("greennexa_telemetry_updated", sync);
      window.removeEventListener("greennexa_day_changed", sync);
    };
  }, [orgId]);

  useEffect(() => {
    const updateAge = () => {
      const baseTime = kpis?.last_updated_at ? new Date(kpis.last_updated_at).getTime() : lastUpdated.getTime();
      const diffSecs = Math.max(0, Math.floor((Date.now() - baseTime) / 1000));
      setSecondsAgo(diffSecs);
    };
    updateAge();
    const timer = setInterval(updateAge, 1000);
    return () => clearInterval(timer);
  }, [kpis?.last_updated_at, lastUpdated]);

  // Use kpis.wards (MunicipalityWard records) — NEVER kpis.blocks (FacilityBlock records)
  const wards: MunicipalityWardItem[] = kpis?.wards || [];
  const activeAnomalyCount = kpis?.active_anomaly_count ?? anomalies.length;
  const criticalCount = kpis?.critical_anomaly_count ?? anomalies.filter((a) => (a as any).severity === "CRITICAL").length;

  const kpiKeys = useMemo(() => Object.keys(kpis?.kpis || {}), [kpis?.kpis]);
  const extras = useDashboardExtras(orgId, kpiKeys);

  /** Per-module telemetry summary — the same source data for every style. */
  const modules = useMemo<ModuleEntry[]>(() => {
    return CIVIC_MODULES.map((mod) => {
      const keys = MODULE_METRICS[mod.label] || { primary: mod.id };
      const kpiData = kpis?.kpis?.[keys.primary] || (keys.fallback ? kpis?.kpis?.[keys.fallback] : undefined);
      const modAnoms = anomalies.filter(
        (a: any) =>
          a.metric === keys.primary ||
          a.sensor_type === keys.primary ||
          (keys.fallback && (a.metric === keys.fallback || a.sensor_type === keys.fallback)) ||
          a.metric === mod.id ||
          a.sensor_type === mod.id
      );
      const hasData = kpiData && kpiData.latest_value != null;
      const valueFormatted = hasData
        ? Number(kpiData.latest_value).toLocaleString(undefined, { maximumFractionDigits: 1 })
        : "—";

      let status: ModuleEntry["status"] = "normal";
      if (modAnoms.some((a: any) => a.severity === "CRITICAL") || kpiData?.anomaly_severity === "CRITICAL") {
        status = "critical";
      } else if (modAnoms.length > 0 || kpiData?.is_anomaly) {
        status = "warning";
      }

      let trendLabel = "+0.0%";
      if (hasData && kpiData.average != null && kpiData.average > 0) {
        const pct = ((Number(kpiData.latest_value) - Number(kpiData.average)) / Number(kpiData.average)) * 100;
        trendLabel = `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
      }

      return {
        id: mod.id,
        label: mod.label,
        icon: mod.icon,
        color: mod.color,
        background: mod.bg,
        href: `/dashboard/modules/${mod.id}`,
        status,
        hasData: Boolean(hasData),
        displayValue: valueFormatted,
        unit: kpiData?.unit || "",
        trendLabel,
        anomaliesCount: modAnoms.length,
      };
    });
  }, [kpis, anomalies]);

  const safeAnomalies = anomalies.filter((a) => !a.status || a.status === "OPEN" || a.status === "ACKNOWLEDGED");
  const optimalScore = typeof kpis?.optimal_score === "number" ? kpis.optimal_score : calculateOptimalScore(safeAnomalies);
  const { color: healthColor, label: healthLabel } = getOptimalScoreColorAndLabel(optimalScore);

  const viewModelInput: DashboardViewModelInput = useMemo(
    () => ({
      scope: "municipality",
      organisationId: orgId,
      organisationName: kpis?.organisation_name || orgName || orgId,
      orgType: kpis?.org_type || "municipality",
      dataSource: kpis?.data_source as any,
      lastUpdatedAt: kpis?.last_updated_at || null,
      isMunicipality: true,
      loading,
      score: { value: optimalScore, label: healthLabel, color: healthColor },
      kpis: (kpis?.kpis as any) || null,
      anomalies: safeAnomalies,
      recommendations,
      wards,
      associatedOrgs,
      modules,
      activeAnomalyCount,
      criticalAnomalyCount: criticalCount,
      isWardUnread: (wardId: string, wardNumber: string) => isWardUnread(wardNumber) || isWardUnread(wardId),
      forecast: extras.forecast,
      trend: extras.trend,
    }),
    [
      orgId,
      orgName,
      kpis,
      loading,
      optimalScore,
      healthLabel,
      healthColor,
      safeAnomalies,
      recommendations,
      wards,
      associatedOrgs,
      modules,
      activeAnomalyCount,
      criticalCount,
      extras.forecast,
      extras.trend,
      isWardUnread,
    ]
  );

  const viewModel = useMemo(() => buildDashboardViewModel(viewModelInput), [viewModelInput]);

  return (
    <>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "var(--clr-primary-light)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Building2 size={20} color="var(--clr-primary)" />
            </div>
            <h1 style={{ fontSize: "26px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
              Municipality Operations Control Center
            </h1>
            <span style={{ fontSize: "11px", fontWeight: 700, padding: "3px 10px", borderRadius: "20px", background: "rgba(99,102,241,0.15)", color: "#818cf8", border: "1px solid rgba(99,102,241,0.3)" }}>
              MUNICIPAL INTELLIGENCE
            </span>
          </div>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", margin: 0 }}>
            Civic operations overview for{" "}
            <strong style={{ color: "var(--clr-text-primary)" }}>{kpis?.organisation_name || orgName || orgId}</strong>
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          {kpis && <DataSourceBadge source={kpis.data_source as any} />}
          <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Updated: {secondsAgo}s ago</span>
          <button onClick={loadData} className="btn btn-outline btn-sm" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {loading && !kpis ? (
        <>
          <CardSkeleton />
          <CardSkeleton />
        </>
      ) : (
        <DashboardRenderer
          vm={viewModel}
          style={style}
          onSelectOrg={(id, name) => setSelectedOrgForView({ id, name })}
        />
      )}

      <p style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "24px" }}>
        Dashboard style: <strong style={{ color: "var(--clr-text-primary)" }}>{definition.label}</strong> — {definition.tagline}. Change it any time from the “…” options menu.
      </p>

      {selectedOrgForView && (
        <MunicipalityOrgOverview
          orgId={selectedOrgForView.id}
          orgName={selectedOrgForView.name}
          isOpen={true}
          onClose={() => setSelectedOrgForView(null)}
        />
      )}
    </>
  );
};
