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
import { Trash2, RefreshCw } from "lucide-react";
import { TimeSeriesWaveform } from "@/components/ui/TimeSeriesWaveform";

export default function WastePage() {
  const { activeOrgId, enabledModules } = useAuth();
  const [stats, setStats] = useState<any | null>(null);
  const [timeseries, setTimeseries] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const isEnabled = !enabledModules || enabledModules.map((m) => m.toLowerCase().trim()).includes("waste");

  const loadData = async () => {
    if (!activeOrgId || !isEnabled) return;
    setLoading(true);
    try {
      const [statsRes, tsRes] = await Promise.allSettled([
        api.get<any>(`/api/v1/dashboard/${activeOrgId}/statistics`, { sensor_type: "waste" }),
        api.get<any>(`/api/v1/dashboard/${activeOrgId}/timeseries`, { sensor_type: "waste", period: "24h" }),
      ]);

      if (statsRes.status === "fulfilled") {
        const raw = statsRes.value?.statistics?.waste || statsRes.value;
        setStats(raw);
      }
      if (tsRes.status === "fulfilled") {
        const rawPts = Array.isArray(tsRes.value) ? tsRes.value : tsRes.value?.data || [];
        setTimeseries(rawPts);
      }
    } catch {
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
          <Trash2 size={48} color="var(--clr-text-muted)" style={{ marginBottom: "16px" }} />
          <h2 style={{ fontSize: "20px", fontWeight: 700, color: "var(--clr-text-primary)", margin: 0 }}>Module Access Restricted</h2>
          <p style={{ color: "var(--clr-text-secondary)", marginTop: "8px", fontSize: "14px" }}>
            The <strong>Waste</strong> module is disabled for your organisation.
          </p>
        </div>
      </AppLayout>
    );
  }


  const avgVal = stats?.avg ?? stats?.average ?? 0;
  const maxVal = stats?.max ?? 0;
  const countVal = stats?.count ?? stats?.total_readings ?? 0;
  const unitStr = stats?.unit || "kg";

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px" }}>
            <Trash2 color="#10b981" /> Waste Intelligence
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)" }}>
            Solid waste accumulation, bin level monitoring, and compaction trends
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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "20px", marginBottom: "32px" }}>
        {loading ? (
          <>
            <Skeleton height="100px" />
            <Skeleton height="100px" />
            <Skeleton height="100px" />
          </>
        ) : stats ? (
          <>
            <MetricCard title="Average Waste Volume" value={Number(avgVal).toFixed(1)} unit={unitStr} subtitle="24h Mean" />
            <MetricCard title="Maximum Recorded" value={Number(maxVal).toFixed(1)} unit={unitStr} subtitle="Peak Bin Fill" />
            <MetricCard title="Total Observations" value={countVal} subtitle="Data Points" />
          </>
        ) : (
          <EmptyState title="No waste data available" description="Waste bin monitoring is currently inactive or disabled." />
        )}
      </div>

      <div className="card" style={{ padding: "24px" }}>
        <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "20px" }}>Waste Fill Volume ({unitStr})</h2>
        <TimeSeriesWaveform
          data={timeseries.map((pt) => ({
            timestamp: pt.timestamp,
            value: pt.value,
            is_anomaly: pt.is_anomaly,
            anomaly_severity: pt.anomaly_severity,
          }))}
          moduleName="waste"
          unit={unitStr}
          locationName="Facility Waste Monitor"
          color="#10b981"
          height={350}
          emptyTitle="No historical chart data"
          emptyDescription="Enable waste sensors in Organisation Settings to view fill data."
        />
      </div>
    </AppLayout>
  );
}
