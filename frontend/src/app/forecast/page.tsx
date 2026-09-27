"use client";

import React, { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { ForecastResponse, SensorMetricType } from "@/types";
import { DataSourceBadge } from "@/components/ui/DataSourceBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { TrendingUp, RefreshCw, AlertCircle } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const FORECAST_MODES = [
  { key: "default", label: "Default" },
  { key: "last", label: "Last" },
  { key: "7d", label: "7 Days" },
  { key: "15d", label: "15 Days" },
  { key: "30d", label: "30 Days" },
];

export default function ForecastPage() {
  const { activeOrgId } = useAuth();
  const [sensorType, setSensorType] = useState<SensorMetricType>("energy");
  const [horizon, setHorizon] = useState<string>("24h");
  const [mode, setMode] = useState<string>("default");
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadForecast = async () => {
    if (!activeOrgId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<ForecastResponse>(`/api/v1/forecast/${activeOrgId}`, {
        sensor_type: sensorType,
        horizon: horizon,
        mode: mode,
      });
      setForecast(res);
    } catch (err: any) {
      setError(err.message || "Failed to generate AI forecast. Ensure historical data exists.");
      setForecast(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadForecast();
  }, [activeOrgId, sensorType, horizon, mode]);

  useEffect(() => {
    const handleDayChange = () => {
      loadForecast();
    };
    window.addEventListener("greennexa_day_changed", handleDayChange);
    return () => window.removeEventListener("greennexa_day_changed", handleDayChange);
  }, [loadForecast]);

  const chartData =
    forecast?.is_available && forecast?.forecast?.length > 0
      ? forecast.forecast.map((pt) => ({
          time: new Date(pt.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          predicted: pt.predicted_value,
          lower: pt.lower_bound,
          upper: pt.upper_bound,
        }))
      : [];

  const avgPredicted =
    chartData.length > 0
      ? (chartData.reduce((acc, curr) => acc + curr.predicted, 0) / chartData.length).toFixed(2)
      : null;

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px" }}>
            <TrendingUp color="var(--clr-primary)" /> AI/ML Forecasting Engine
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)" }}>
            Short-term predictive modeling using Holt-Winters exponential smoothing & transparent multi-window modes
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {forecast && <DataSourceBadge source={forecast.data_source} />}
          <button onClick={loadForecast} className="btn btn-outline btn-sm">
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Control Bar: Metric Selector, Mode Selector & Horizon Toggles */}
      <div className="card" style={{ padding: "16px 20px", marginBottom: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
        {/* Row 1: Metric & Horizon */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600 }}>Metric:</span>
            {(["energy", "water"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setSensorType(m)}
                className={`btn btn-sm ${sensorType === m ? "btn-primary" : "btn-outline"}`}
                style={{ textTransform: "capitalize" }}
              >
                {m}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600 }}>Forecast Horizon:</span>
            {["6h", "12h", "24h", "48h", "72h"].map((h) => (
              <button
                key={h}
                onClick={() => setHorizon(h)}
                className={`btn btn-sm ${horizon === h ? "btn-accent" : "btn-outline"}`}
              >
                {h}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: 5 Forecasting Modes (Feature 3) */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", borderTop: "1px solid var(--clr-border)", paddingTop: "12px", flexWrap: "wrap" }}>
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-text-secondary)" }}>
            Observation Window:
          </span>
          {FORECAST_MODES.map((m) => {
            const isSelected = mode === m.key;
            return (
              <button
                key={m.key}
                onClick={() => setMode(m.key)}
                className="btn btn-sm"
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  backgroundColor: isSelected ? "var(--clr-primary)" : "var(--clr-surface-2)",
                  color: isSelected ? "#ffffff" : "var(--clr-text-primary)",
                  border: isSelected ? "1px solid var(--clr-primary)" : "1px solid var(--clr-border)",
                }}
              >
                {m.label}
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <div style={{ padding: "16px", borderRadius: "12px", background: "#fee2e2", border: "1px solid #fca5a5", color: "#b91c1c", marginBottom: "24px", display: "flex", alignItems: "center", gap: "10px" }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Honest Incomplete Data Notice (Feature 3 requirement: no fake forecasts) */}
      {!loading && forecast && forecast.is_available === false && (
        <div
          className="card"
          style={{
            padding: "24px",
            marginBottom: "24px",
            border: "1px solid rgba(245, 158, 11, 0.4)",
            backgroundColor: "rgba(245, 158, 11, 0.05)",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: "14px" }}>
            <div
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "10px",
                backgroundColor: "rgba(245, 158, 11, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <AlertCircle size={24} color="#f59e0b" />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0, color: "#f59e0b" }}>
                  {forecast.status_message || "Forecast Unavailable"}
                </h3>
                {forecast.required_days && (
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      padding: "2px 8px",
                      borderRadius: "10px",
                      backgroundColor: "rgba(245, 158, 11, 0.2)",
                      color: "#d97706",
                    }}
                  >
                    {forecast.available_days ?? 0}/{forecast.required_days} Days Available
                  </span>
                )}
              </div>

              <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: "0 0 12px 0" }}>
                GreenNexa enforces honest predictive analytics. When simulated day changes occur or multi-day observation spans are incomplete, synthetic extrapolations are suppressed to avoid misleading operational decisions.
              </p>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "12px",
                  background: "var(--clr-surface-1)",
                  padding: "12px 16px",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              >
                <div>
                  <span style={{ color: "var(--clr-text-muted)" }}>Current Value: </span>
                  <strong>{forecast.current_value !== null && forecast.current_value !== undefined ? `${forecast.current_value} ${forecast.unit || ""}` : "Awaiting readings"}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--clr-text-muted)" }}>Threshold Reference: </span>
                  <span>{forecast.historical_comparison || "Standard facility configuration"}</span>
                </div>
                <div>
                  <span style={{ color: "var(--clr-text-muted)" }}>Model Basis: </span>
                  <span>{forecast.basis || "Requires multi-point telemetry"}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Forecast Chart & Insights (When forecast is available) */}
      <div className="card" style={{ padding: "24px", marginBottom: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 700, textTransform: "capitalize" }}>
            {sensorType} Forecast ({horizon} horizon — {mode.toUpperCase()} mode)
          </h2>
          {forecast && forecast.is_available && (
            <span style={{ fontSize: "12px", color: "var(--clr-text-muted)", background: "var(--clr-surface-2)", padding: "4px 10px", borderRadius: "6px" }}>
              Algorithm: <strong>{forecast.model}</strong>
            </span>
          )}
        </div>

        {loading ? (
          <Skeleton height="350px" />
        ) : chartData.length > 0 ? (
          <>
            {/* KPI Strip */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
                marginBottom: "20px",
              }}
            >
              <div style={{ background: "var(--clr-surface-2)", padding: "12px 16px", borderRadius: "8px" }}>
                <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                  Current Value
                </div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                  {forecast?.current_value ?? "-"} {forecast?.unit}
                </div>
              </div>

              <div style={{ background: "var(--clr-surface-2)", padding: "12px 16px", borderRadius: "8px" }}>
                <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                  Projected Horizon Avg
                </div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-primary)" }}>
                  {avgPredicted ?? "-"} {forecast?.unit}
                </div>
              </div>

              <div style={{ background: "var(--clr-surface-2)", padding: "12px 16px", borderRadius: "8px" }}>
                <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                  Available Observations
                </div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                  {forecast?.available_days ?? 1} day(s)
                </div>
              </div>
            </div>

            <div style={{ width: "100%", height: 360 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--clr-border-light)" />
                  <XAxis dataKey="time" stroke="var(--clr-text-muted)" fontSize={12} />
                  <YAxis stroke="var(--clr-text-muted)" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--clr-surface)",
                      borderColor: "var(--clr-border)",
                      borderRadius: "8px",
                      color: "var(--clr-text-primary)",
                      boxShadow: "0 8px 24px rgba(0, 0, 0, 0.25)"
                    }}
                    itemStyle={{ color: "var(--clr-text-primary)" }}
                    labelStyle={{ color: "var(--clr-text-secondary)", fontWeight: 600 }}
                  />
                  {/* 95% Confidence Interval Band */}
                  <Area type="monotone" dataKey="upper" stroke="none" fill="rgba(34, 197, 94, 0.15)" />
                  <Area type="monotone" dataKey="lower" stroke="none" fill="rgba(34, 197, 94, 0.15)" />
                  <Area type="monotone" dataKey="predicted" stroke="var(--clr-primary)" fill="none" strokeWidth={3} strokeDasharray="5 5" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Model Basis & Historical Comparison Notes */}
            {forecast?.historical_comparison && (
              <div
                style={{
                  marginTop: "20px",
                  padding: "12px 16px",
                  borderRadius: "8px",
                  backgroundColor: "var(--clr-surface-2)",
                  fontSize: "12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px",
                }}
              >
                <div>
                  <strong>Historical Baseline Comparison: </strong>
                  <span style={{ color: "var(--clr-text-secondary)" }}>{forecast.historical_comparison}</span>
                </div>
                {forecast.basis && (
                  <div>
                    <strong>Calculation Basis: </strong>
                    <span style={{ color: "var(--clr-text-secondary)" }}>{forecast.basis}</span>
                  </div>
                )}
                {forecast.assumptions && (
                  <div>
                    <strong>Model Assumptions: </strong>
                    <span style={{ color: "var(--clr-text-secondary)" }}>{forecast.assumptions}</span>
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <EmptyState
            title="Insufficient historical data"
            description="The forecasting engine requires prior sensor readings to build time-series models."
          />
        )}

        {/* Disclaimer Notice */}
        <div className="info-box" style={{ marginTop: "20px" }}>
          ⚠️ <strong>Disclaimer:</strong> Forecast values are short-term AI estimates and not guaranteed future measurements.
        </div>
      </div>
    </AppLayout>
  );
}
