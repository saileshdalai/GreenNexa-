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
import { Thermometer, Wind, Cloud, RefreshCw } from "lucide-react";
import { TimeSeriesWaveform } from "@/components/ui/TimeSeriesWaveform";

export default function EnvironmentPage() {
  const { activeOrgId, enabledModules } = useAuth();
  const [selectedSensor, setSelectedSensor] = useState<"temperature" | "humidity" | "co2">("temperature");
  const [tempData, setTempData] = useState<TimeSeriesPoint[]>([]);
  const [humidityData, setHumidityData] = useState<TimeSeriesPoint[]>([]);
  const [co2Data, setCo2Data] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const isEnabled = !enabledModules || ["air_quality", "temperature", "humidity", "co2", "environment", "climate"].some((k) => enabledModules.map((m) => m.toLowerCase().trim()).includes(k));

  const loadData = async () => {
    if (!activeOrgId || !isEnabled) return;
    setLoading(true);
    try {
      const [tRes, hRes, cRes] = await Promise.allSettled([
        api.get<TimeSeriesPoint[]>(`/api/v1/dashboard/${activeOrgId}/timeseries`, { sensor_type: "temperature", period: "24h" }),
        api.get<TimeSeriesPoint[]>(`/api/v1/dashboard/${activeOrgId}/timeseries`, { sensor_type: "humidity", period: "24h" }),
        api.get<TimeSeriesPoint[]>(`/api/v1/dashboard/${activeOrgId}/timeseries`, { sensor_type: "co2", period: "24h" }),
      ]);

      if (tRes.status === "fulfilled") setTempData(tRes.value);
      if (hRes.status === "fulfilled") setHumidityData(hRes.value);
      if (cRes.status === "fulfilled") setCo2Data(cRes.value);
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
          <Thermometer size={48} color="var(--clr-text-muted)" style={{ marginBottom: "16px" }} />
          <h2 style={{ fontSize: "20px", fontWeight: 700, color: "var(--clr-text-primary)", margin: 0 }}>Module Access Restricted</h2>
          <p style={{ color: "var(--clr-text-secondary)", marginTop: "8px", fontSize: "14px" }}>
            The <strong>Environment</strong> module is disabled for your organisation.
          </p>
        </div>
      </AppLayout>
    );
  }

  const activeData = selectedSensor === "temperature" ? tempData : selectedSensor === "humidity" ? humidityData : co2Data;


  const latestTemp = tempData.length > 0 ? tempData[tempData.length - 1].value.toFixed(1) : "N/A";
  const latestHum = humidityData.length > 0 ? humidityData[humidityData.length - 1].value.toFixed(1) : "N/A";
  const latestCo2 = co2Data.length > 0 ? co2Data[co2Data.length - 1].value.toFixed(0) : "N/A";

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px" }}>
            <Thermometer color="#ef4444" /> Environmental Quality
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)" }}>
            Ambient temperature, humidity level, and CO₂ air quality monitoring
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {tempData.length > 0 && <DataSourceBadge source={tempData[0].source} />}
          <button onClick={loadData} className="btn btn-outline btn-sm">
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", marginBottom: "32px" }}>
        {loading ? (
          <>
            <Skeleton height="100px" />
            <Skeleton height="100px" />
            <Skeleton height="100px" />
          </>
        ) : (
          <>
            <MetricCard title="Indoor Temperature" value={latestTemp} unit="°C" icon={<Thermometer size={20} />} color="rgba(239, 68, 68, 0.15)" />
            <MetricCard title="Relative Humidity" value={latestHum} unit="%" icon={<Wind size={20} />} color="rgba(59, 130, 246, 0.15)" />
            <MetricCard title="CO₂ Concentration" value={latestCo2} unit="ppm" icon={<Cloud size={20} />} color="rgba(107, 114, 128, 0.15)" />
          </>
        )}
      </div>

      {/* Sensor Selector & Chart */}
      <div className="card" style={{ padding: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 700 }}>24-Hour Environmental Trend</h2>

          <div style={{ display: "flex", gap: "8px" }}>
            {(["temperature", "humidity", "co2"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setSelectedSensor(s)}
                className={`btn btn-sm ${selectedSensor === s ? "btn-primary" : "btn-outline"}`}
                style={{ textTransform: "capitalize" }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <TimeSeriesWaveform
          data={activeData.map((pt) => ({
            timestamp: pt.timestamp,
            value: pt.value,
            is_anomaly: pt.is_anomaly,
            anomaly_severity: pt.anomaly_severity,
          }))}
          moduleName={selectedSensor}
          unit={selectedSensor === "temperature" ? "°C" : selectedSensor === "humidity" ? "%" : "ppm"}
          locationName={`Environmental ${selectedSensor.toUpperCase()}`}
          color={selectedSensor === "temperature" ? "#ef4444" : selectedSensor === "humidity" ? "#3b82f6" : "#8b5cf6"}
          isCumulative={false}
          height={350}
          emptyTitle="No environmental data"
          emptyDescription={`No ${selectedSensor} readings recorded.`}
        />
      </div>
    </AppLayout>
  );
}
