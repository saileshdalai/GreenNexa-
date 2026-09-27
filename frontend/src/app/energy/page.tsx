"use client";

import React, { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { TimeSeriesPoint } from "@/types";
import { MetricCard } from "@/components/ui/Card";
import { DataSourceBadge } from "@/components/ui/DataSourceBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Zap, RefreshCw } from "lucide-react";
import { TimeSeriesWaveform } from "@/components/ui/TimeSeriesWaveform";

export default function EnergyPage() {
  const { activeOrgId, enabledModules } = useAuth();
  const [stats, setStats] = useState<any | null>(null);
  const [timeseries, setTimeseries] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const isEnabled = !enabledModules || enabledModules.map((m) => m.toLowerCase().trim()).includes("energy");

  const loadData = async () => {
    if (!activeOrgId || !isEnabled) return;
    setLoading(true);
    setError(null);
    try {
      const [statsRes, tsRes] = await Promise.allSettled([
        api.get<any>(`/api/v1/dashboard/${activeOrgId}/statistics`, { sensor_type: "energy" }),
        api.get<any>(`/api/v1/dashboard/${activeOrgId}/timeseries`, { sensor_type: "energy", period: "24h" }),
      ]);

      if (statsRes.status === "fulfilled") {
        const raw = statsRes.value?.statistics?.energy || statsRes.value;
        setStats(raw);
      }
      if (tsRes.status === "fulfilled") {
        const rawPts = Array.isArray(tsRes.value) ? tsRes.value : tsRes.value?.data || [];
        setTimeseries(rawPts);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load energy metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeOrgId, enabledModules]);

  if (enabledModules && !isEnabled) {
    return (
      <AppLayout>
        <div style={{ padding: "40px 20px", textAlign: "center", background: "var(--clr-surface-2)", borderRadius: "12px", margin: "24px 0", border: "1px solid var(--clr-border)" }}>
          <Zap size={48} color="var(--clr-text-muted)" style={{ marginBottom: "16px" }} />
          <h2 style={{ fontSize: "20px", fontWeight: 700, color: "var(--clr-text-primary)", margin: 0 }}>Module Access Restricted</h2>
          <p style={{ color: "var(--clr-text-secondary)", marginTop: "8px", fontSize: "14px" }}>
            The <strong>Energy</strong> module is disabled for your organisation.
          </p>
        </div>
      </AppLayout>
    );
  }


  const avgVal = stats?.avg ?? stats?.average ?? 0;
  const maxVal = stats?.max ?? 0;
  const minVal = stats?.min ?? 0;
  const countVal = stats?.count ?? stats?.total_readings ?? 0;
  const unitStr = stats?.unit || "kWh";

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px" }}>
            <Zap color="var(--clr-primary)" /> Energy Intelligence
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)" }}>
            Electricity consumption metrics, statistics, and 24-hour historical trend
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {timeseries.length > 0 && <DataSourceBadge source={timeseries[0].source} />}
          <button onClick={loadData} className="btn btn-outline btn-sm">
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && <div style={{ padding: "16px", borderRadius: "12px", background: "#fee2e2", color: "#b91c1c", marginBottom: "24px" }}>{error}</div>}

      {/* Stats Summary Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "20px", marginBottom: "32px" }}>
        {loading ? (
          <>
            <Skeleton height="100px" />
            <Skeleton height="100px" />
            <Skeleton height="100px" />
            <Skeleton height="100px" />
          </>
        ) : stats ? (
          <>
            <MetricCard title="Average Consumption" value={Number(avgVal).toFixed(1)} unit={unitStr} subtitle="24h Average" />
            <MetricCard title="Peak Demand (Max)" value={Number(maxVal).toFixed(1)} unit={unitStr} subtitle="24h Peak" />
            <MetricCard title="Minimum Demand (Min)" value={Number(minVal).toFixed(1)} unit={unitStr} subtitle="24h Baseline" />
            <MetricCard title="Reading Samples" value={countVal} subtitle="Data Points Collected" />
          </>
        ) : (
          <EmptyState title="No statistics available" description="Energy sensor readings have not been recorded yet." />
        )}
      </div>

      {/* Historical Trend Chart */}
      <div className="card" style={{ padding: "24px", marginBottom: "32px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "20px" }}>Historical Electricity Usage (kWh)</h2>
        <TimeSeriesWaveform
          data={timeseries.map((pt) => ({
            timestamp: pt.timestamp,
            value: pt.value,
            is_anomaly: pt.is_anomaly,
            anomaly_severity: pt.anomaly_severity,
          }))}
          moduleName="energy"
          unit={unitStr}
          locationName="Facility Energy Monitor"
          color="#f59e0b"
          isCumulative={true}
          height={350}
          emptyTitle="No historical chart data"
          emptyDescription="Sensor readings will populate as data is generated."
        />
      </div>
    </AppLayout>
  );
}
