"use client";

import React, { useEffect, useMemo, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useDashboardStyle } from "@/context/DashboardStyleContext";
import { api } from "@/lib/api";
import { DashboardKPIs, AnomalyRecord, AIRecommendation, AnomalyListResponse, RecommendationListResponse } from "@/types";
import { DataSourceBadge } from "@/components/ui/DataSourceBadge";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { RefreshCw } from "lucide-react";
import { MunicipalityDashboard } from "@/components/municipality/MunicipalityDashboard";
import { isMunicipality } from "@/lib/organisation";
import { DashboardRenderer } from "@/components/dashboard/DashboardRenderer";
import { buildDashboardViewModel } from "@/components/dashboard/dashboardViewModel";
import { useDashboardExtras } from "@/components/dashboard/useDashboardExtras";

import { useSearchParams } from "next/navigation";
import { calculateOptimalScore, getOptimalScoreColorAndLabel } from "@/lib/scoring";

interface RecentReadingItem {
  id: string;
  sensor_type: string;
  value: number;
  unit: string;
  source: string;
  timestamp: string;
  is_anomaly: boolean;
}

function DashboardContent() {
  const { user, activeOrgId, setActiveOrgId, currentOrg, organisations = [] } = useAuth();
  const { style, definition } = useDashboardStyle();
  const searchParams = useSearchParams();
  const queryOrg = searchParams.get("org");

  // Resolve effective organisation ID for dashboard requests
  const effectiveOrgId = React.useMemo(() => {
    if (user?.role === "SUPER_ADMIN") {
      return queryOrg || activeOrgId || user.organisation_id || (organisations.length > 0 ? organisations[0].id : "ORG-00001");
    }
    // For ADMIN role, strictly enforce authenticated user's organisation_id
    return user?.organisation_id || null;
  }, [user, activeOrgId, queryOrg, organisations]);

  // Synchronize AuthContext if Super Admin provides a query parameter
  useEffect(() => {
    if (user?.role === "SUPER_ADMIN" && queryOrg && queryOrg !== activeOrgId) {
      setActiveOrgId(queryOrg);
    }
  }, [user, queryOrg, activeOrgId]);

  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [recentReadings, setRecentReadings] = useState<RecentReadingItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [secondsAgo, setSecondsAgo] = useState<number>(0);
  // Detect Municipality org type — used to switch dashboard scope
  const [isMunicipalityOrg, setIsMunicipalityOrg] = useState<boolean>(false);

  // Sync isMunicipalityOrg
  useEffect(() => {
    if (currentOrg && (currentOrg.id === effectiveOrgId)) {
      setIsMunicipalityOrg(isMunicipality(currentOrg));
    } else if (kpis) {
      setIsMunicipalityOrg(isMunicipality(kpis));
    }
  }, [currentOrg, kpis, effectiveOrgId]);

  const loadDashboardData = async () => {
    if (!effectiveOrgId) return;
    setLoading(true);
    setError(null);
    try {
      const [kpiRes, anomalyRes, recRes, recentRes] = await Promise.allSettled([
        api.get<DashboardKPIs>(`/api/v1/dashboard/${effectiveOrgId}`),
        api.get<AnomalyListResponse | AnomalyRecord[]>(`/api/v1/anomalies`, { organisation_id: effectiveOrgId, limit: 5, status: "OPEN" }),
        api.get<RecommendationListResponse | AIRecommendation[]>(`/api/v1/recommendations`, { organisation_id: effectiveOrgId, status: "OPEN" }),
        api.get<{ readings: RecentReadingItem[] }>(`/api/v1/dashboard/${effectiveOrgId}/recent?limit=6`),
      ]);

      if (kpiRes.status === "fulfilled") {
        const newKpis = kpiRes.value;
        setKpis(newKpis);
        setIsMunicipalityOrg(isMunicipality(newKpis) || (currentOrg ? isMunicipality(currentOrg) : false));

        // Use backend telemetry freshness timestamp
        if (newKpis?.last_updated_at) {
          const remoteDt = new Date(newKpis.last_updated_at);
          setLastUpdated(remoteDt);
          if (typeof window !== "undefined") {
            const prevTs = localStorage.getItem("greennexa_last_telemetry_ts");
            const newTs = remoteDt.toISOString();
            if (prevTs !== newTs) {
              localStorage.setItem("greennexa_last_telemetry_ts", newTs);
              localStorage.setItem("greennexa_sim_cycle_start_ms", String(Date.now()));
              window.dispatchEvent(new CustomEvent("greennexa_telemetry_updated"));
            }
          }
        }
      } else {
        const errObj = kpiRes.reason as any;
        const errStatus = errObj?.status;
        if (errStatus === 403) {
          setError("Access denied: You can only access data for your own organisation.");
        } else if (errStatus === 404) {
          setError(`Organisation '${effectiveOrgId}' was not found.`);
        } else {
          setError(errObj?.message || "Failed to fetch dashboard metrics. Please ensure organisation setup is complete.");
        }
      }

      if (anomalyRes.status === "fulfilled" && anomalyRes.value) {
        const val = anomalyRes.value;
        const list = Array.isArray(val) ? val : Array.isArray((val as AnomalyListResponse)?.items) ? (val as AnomalyListResponse).items : [];
        setAnomalies(list);
      } else {
        setAnomalies([]);
      }

      if (recRes.status === "fulfilled" && recRes.value) {
        const val = recRes.value;
        const list = Array.isArray(val) ? val : Array.isArray((val as RecommendationListResponse)?.items) ? (val as RecommendationListResponse).items : [];
        const activeList = list.filter((r) => r.status === "OPEN" || r.status === "ACTIVE");
        setRecommendations(activeList);
      } else {
        setRecommendations([]);
      }

      if (recentRes.status === "fulfilled" && recentRes.value?.readings) {
        setRecentReadings(recentRes.value.readings);
      }
    } catch (err: any) {
      setError(err.message || "Error loading dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    // 30-second automatic polling for live data refresh
    const pollInterval = setInterval(loadDashboardData, 30000);

    const handleSync = () => {
      loadDashboardData();
    };
    window.addEventListener("greennexa_demo_mode_changed", handleSync);
    window.addEventListener("greennexa_anomaly_updated", handleSync);
    window.addEventListener("greennexa_day_changed", handleSync);
    window.addEventListener("greennexa_telemetry_updated", handleSync);

    return () => {
      clearInterval(pollInterval);
      window.removeEventListener("greennexa_demo_mode_changed", handleSync);
      window.removeEventListener("greennexa_anomaly_updated", handleSync);
      window.removeEventListener("greennexa_day_changed", handleSync);
      window.removeEventListener("greennexa_telemetry_updated", handleSync);
    };
  }, [effectiveOrgId]);

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

  // Trend + forecast data are style-independent and fetched once per metric.
  const kpiKeys = useMemo(() => Object.keys(kpis?.kpis || {}), [kpis?.kpis]);
  const extras = useDashboardExtras(isMunicipalityOrg ? null : effectiveOrgId, kpiKeys);

  // Safe active anomalies list for fallback calculations
  const safeAnomalies = (Array.isArray(anomalies) ? anomalies : []).filter(
    (a) => !a.status || a.status === "OPEN" || a.status === "ACKNOWLEDGED"
  );
  const optimalScore = typeof kpis?.optimal_score === "number"
    ? kpis.optimal_score
    : calculateOptimalScore(safeAnomalies);
  const activeAnomalyCount = typeof kpis?.active_anomaly_count === "number"
    ? kpis.active_anomaly_count
    : safeAnomalies.length;
  const { color: healthColor, label: healthLabel } = getOptimalScoreColorAndLabel(optimalScore);

  const viewModel = useMemo(
    () =>
      buildDashboardViewModel({
        scope: "facility",
        organisationId: effectiveOrgId || "",
        organisationName: kpis?.organisation_name || activeOrgId || undefined,
        orgType: (kpis as any)?.org_type || (currentOrg as any)?.org_type,
        facilityName: (kpis as any)?.facility_name,
        dataSource: kpis?.data_source as any,
        lastUpdatedAt: kpis?.last_updated_at || null,
        isMunicipality: false,
        loading,
        score: { value: optimalScore, label: healthLabel, color: healthColor },
        kpis: (kpis?.kpis as any) || null,
        legacyMetrics: (kpis as any)?.metrics || null,
        anomalies: safeAnomalies,
        recommendations,
        recentReadings,
        activeAnomalyCount,
        forecast: extras.forecast,
        trend: extras.trend,
      }),
    [
      effectiveOrgId,
      kpis,
      activeOrgId,
      currentOrg,
      loading,
      optimalScore,
      healthLabel,
      healthColor,
      safeAnomalies,
      recommendations,
      recentReadings,
      activeAnomalyCount,
      extras.forecast,
      extras.trend,
    ]
  );

  return (
    <AppLayout>
      {/* Municipality orgs get their own dedicated dashboard (also style-aware) */}
      {isMunicipalityOrg && effectiveOrgId && (
        <MunicipalityDashboard orgId={effectiveOrgId} orgName={kpis?.organisation_name} />
      )}

      {/* Standard Facility Dashboard — hidden for Municipality orgs */}
      {!isMunicipalityOrg && <>
      {/* Header Bar */}

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
            Facility Dashboard
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", margin: "4px 0 0 0" }}>
            Real-time intelligence for {kpis?.organisation_name || activeOrgId || "Organisation"}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          {kpis && <DataSourceBadge source={kpis.data_source} />}
          <span style={{ fontSize: "12px", color: "var(--clr-text-muted)", opacity: 0.9 }}>
            Last updated: {secondsAgo}s ago
          </span>
          <button
            onClick={loadDashboardData}
            className="btn btn-outline btn-sm"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
            title="Refresh metrics now"
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Refresh Now</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "16px", borderRadius: "12px", background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#fca5a5", marginBottom: "24px", fontSize: "14px" }}>
          {error}
        </div>
      )}

      {loading && !kpis ? (
        <>
          <CardSkeleton />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", marginTop: "20px" }}>
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        </>
      ) : (
        <DashboardRenderer vm={viewModel} style={style} />
      )}

      <p style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "24px" }}>
        Dashboard style: <strong style={{ color: "var(--clr-text-primary)" }}>{definition.label}</strong> — {definition.tagline}. Change it any time from the “…” options menu.
      </p>
      {/* Close non-municipality fragment */}
      </>}
    </AppLayout>
  );
}


export default function DashboardPage() {
  return (
    <React.Suspense fallback={<div style={{ padding: "2rem", color: "var(--clr-text-secondary)" }}>Loading Dashboard...</div>}>
      <DashboardContent />
    </React.Suspense>
  );
}
