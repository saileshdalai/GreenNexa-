"use client";

import React, { useId, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { TrendPointItem } from "@/types";
import { Activity, AlertTriangle, Layers, Info } from "lucide-react";

export interface TimeSeriesWaveformProps {
  data: TrendPointItem[];
  moduleName?: string;
  unit: string;
  locationName?: string;
  baseline?: number | null;
  warningThreshold?: number | null;
  criticalThreshold?: number | null;
  isCumulative?: boolean;
  color?: string;
  height?: number;
  period?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  hideHeader?: boolean;
  currentValue?: number | null;
  activeAnomalyCount?: number;
}

const MODULE_COLOR_MAP: Record<string, string> = {
  energy: "#f59e0b",       // Amber
  water: "#3b82f6",        // Blue
  waste: "#10b981",        // Emerald
  temperature: "#ef4444",  // Red
  climate: "#ef4444",      // Red
  air_quality: "#8b5cf6",  // Purple
  humidity: "#06b6d4",     // Cyan
  co2: "#a855f7",          // Purple
  traffic: "#eab308",      // Yellow
  parking: "#6366f1",      // Indigo
  assets: "#14b8a6",       // Teal
  safety: "#ef4444",       // Coral Red
};

export function TimeSeriesWaveform({
  data,
  moduleName = "sensor",
  unit,
  locationName = "Facility",
  baseline = null,
  warningThreshold = null,
  criticalThreshold = null,
  isCumulative = false,
  color,
  height = 280,
  period = "24h",
  emptyTitle = "No sensor data available yet.",
  emptyDescription = "Readings will automatically appear as live telemetry or Demo Mode arrives.",
  hideHeader = false,
  currentValue = null,
  activeAnomalyCount = 0,
}: TimeSeriesWaveformProps) {
  const gradientId = useId();
  const [showReferenceLines, setShowReferenceLines] = useState<boolean>(true);

  const cleanModule = (moduleName || "sensor").toLowerCase().trim();
  const strokeColor = color || MODULE_COLOR_MAP[cleanModule] || "var(--clr-primary, #10b981)";

  // Format data: retain actual telemetry readings without artificial staircase mutation
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    return data.map((pt, idx) => {
      const rawVal = Number(pt.value);
      const safeVal = isNaN(rawVal) ? 0 : rawVal;

      const dateObj = new Date(pt.timestamp);
      const isValidDate = !isNaN(dateObj.getTime());

      let formattedTime = "";
      if (isValidDate) {
        if (period === "7d") {
          formattedTime = dateObj.toLocaleDateString([], { weekday: "short" }) + " " + dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } else if (period === "30d") {
          formattedTime = dateObj.toLocaleDateString([], { month: "short", day: "numeric" });
        } else {
          formattedTime = dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        }
      } else {
        formattedTime = `Pt ${idx + 1}`;
      }

      return {
        ...pt,
        displayValue: safeVal,
        formattedTime,
        numericTime: isValidDate ? dateObj.getTime() : idx,
      };
    });
  }, [data, period]);

  // Compute stats for header display: prioritize authoritative currentValue passed from domain
  const latestPoint = chartData.length > 0 ? chartData[chartData.length - 1] : null;
  const targetCurrent = currentValue != null ? currentValue : latestPoint?.displayValue;
  const currentValFormatted = targetCurrent != null
    ? targetCurrent.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })
    : null;

  const hasAnomalies = chartData.some((p) => p.is_anomaly);

  // Custom Dot Renderer for Anomaly Highlighting
  const renderCustomDot = (props: any) => {
    const { cx, cy, payload } = props;
    if (!cx || !cy || !payload) return null;

    if (payload.is_anomaly) {
      const isCritical = payload.anomaly_severity === "CRITICAL";
      const dotFill = isCritical ? "#ef4444" : "#f59e0b";
      return (
        <g key={`anom-dot-${payload.timestamp || cx}`}>
          <circle cx={cx} cy={cy} r={6} fill={dotFill} stroke="#ffffff" strokeWidth={2} />
          <circle cx={cx} cy={cy} r={10} fill="none" stroke={dotFill} strokeWidth={1.5} opacity={0.6} />
        </g>
      );
    }
    return null;
  };

  // Custom Interactive Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const pt = payload[0].payload;
      const dateObj = new Date(pt.timestamp);
      const fullDateStr = !isNaN(dateObj.getTime())
        ? dateObj.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" }) +
          " " +
          dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
        : pt.timestamp;

      const valStr = typeof pt.displayValue === "number"
        ? pt.displayValue.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })
        : pt.displayValue;

      const baseVal = pt.baseline ?? baseline;
      const deviation = baseVal && baseVal > 0
        ? (((pt.displayValue - baseVal) / baseVal) * 100).toFixed(1)
        : null;

      return (
        <div
          style={{
            background: "var(--clr-surface-2, #1e293b)",
            border: "1px solid var(--clr-border, #334155)",
            borderRadius: "10px",
            padding: "12px 16px",
            boxShadow: "0 12px 28px rgba(0, 0, 0, 0.45)",
            fontSize: "12px",
            minWidth: "200px",
            backdropFilter: "blur(10px)",
            pointerEvents: "none",
          }}
        >
          <div style={{ color: "var(--clr-text-muted, #94a3b8)", fontSize: "11px", marginBottom: "4px" }}>
            {fullDateStr}
          </div>
          <div style={{ fontWeight: 700, color: "var(--clr-text-primary, #f8fafc)", fontSize: "13px", marginBottom: "6px" }}>
            {locationName}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "6px", marginBottom: "6px" }}>
            <span style={{ fontSize: "20px", fontWeight: 800, color: strokeColor }}>
              {valStr}
            </span>
            <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--clr-text-secondary, #cbd5e1)" }}>
              {unit}
            </span>
          </div>

          {pt.is_anomaly && (
            <div
              style={{
                marginTop: "6px",
                padding: "4px 8px",
                borderRadius: "6px",
                background: pt.anomaly_severity === "CRITICAL" ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)",
                border: `1px solid ${pt.anomaly_severity === "CRITICAL" ? "#ef4444" : "#f59e0b"}`,
                color: pt.anomaly_severity === "CRITICAL" ? "#fca5a5" : "#fcd34d",
                fontWeight: 700,
                fontSize: "11px",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              ⚠️ {pt.anomaly_severity || "CRITICAL"} ANOMALY
            </div>
          )}

          {baseVal != null && (
            <div style={{ marginTop: "6px", fontSize: "11px", color: "var(--clr-text-muted, #94a3b8)" }}>
              Baseline: {baseVal} {unit}
              {deviation && (
                <span
                  style={{
                    color: Number(deviation) > 0 ? "#f59e0b" : "#10b981",
                    marginLeft: "6px",
                    fontWeight: 600,
                  }}
                >
                  ({Number(deviation) > 0 ? `+${deviation}%` : `${deviation}%`})
                </span>
              )}
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  // Empty state handling
  if (!chartData || chartData.length === 0) {
    return (
      <div
        style={{
          height: `${height}px`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--clr-surface-2, rgba(255, 255, 255, 0.02))",
          borderRadius: "12px",
          border: "1px dashed var(--clr-border, #334155)",
          padding: "24px",
          textAlign: "center",
        }}
      >
        <Activity size={32} color="var(--clr-text-muted, #64748b)" style={{ marginBottom: "12px", opacity: 0.7 }} />
        <h4 style={{ fontSize: "15px", fontWeight: 700, color: "var(--clr-text-primary, #f8fafc)", margin: 0 }}>
          {emptyTitle}
        </h4>
        <p style={{ fontSize: "13px", color: "var(--clr-text-muted, #94a3b8)", marginTop: "6px", maxWidth: "380px" }}>
          {emptyDescription}
        </p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%" }}>
      {!hideHeader && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
            marginBottom: "16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {currentValFormatted && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "baseline",
                  gap: "6px",
                  background: "var(--clr-surface-2, rgba(255, 255, 255, 0.05))",
                  padding: "4px 12px",
                  borderRadius: "8px",
                  border: "1px solid var(--clr-border, #334155)",
                }}
              >
                <span style={{ fontSize: "11px", color: "var(--clr-text-muted, #94a3b8)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Current:
                </span>
                <span style={{ fontSize: "15px", fontWeight: 800, color: strokeColor }}>
                  {currentValFormatted} {unit}
                </span>
              </div>
            )}

            {hasAnomalies && (
              activeAnomalyCount > 0 ? (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    color: "#ef4444",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    background: "rgba(239, 68, 68, 0.12)",
                    padding: "4px 8px",
                    borderRadius: "6px",
                    border: "1px solid rgba(239, 68, 68, 0.25)",
                  }}
                >
                  <AlertTriangle size={12} /> {activeAnomalyCount} Active Anomal{activeAnomalyCount === 1 ? "y" : "ies"}
                </span>
              ) : (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    color: "var(--clr-text-secondary, #94a3b8)",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    background: "rgba(148, 163, 184, 0.1)",
                    padding: "4px 8px",
                    borderRadius: "6px",
                    border: "1px solid rgba(148, 163, 184, 0.25)",
                  }}
                >
                  <Info size={12} color="#60a5fa" /> Historical anomaly points highlighted
                </span>
              )
            )}
          </div>

          {(baseline != null || warningThreshold != null || criticalThreshold != null) && (
            <button
              onClick={() => setShowReferenceLines(!showReferenceLines)}
              className="btn btn-outline btn-sm"
              style={{
                fontSize: "11px",
                padding: "3px 8px",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                background: showReferenceLines ? "var(--clr-surface-2, rgba(255,255,255,0.06))" : "transparent",
              }}
              title="Toggle baseline and threshold reference overlays"
            >
              <Layers size={12} />
              {showReferenceLines ? "Hide Reference Lines" : "Show Reference Lines"}
            </button>
          )}
        </div>
      )}

      <div style={{ width: "100%", height: `${height}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 12, right: 20, left: -10, bottom: 4 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={strokeColor} stopOpacity={0.28} />
                <stop offset="95%" stopColor={strokeColor} stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="var(--clr-border, #334155)" opacity={0.35} vertical={false} />

            <XAxis
              dataKey="formattedTime"
              stroke="var(--clr-text-muted, #94a3b8)"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "var(--clr-border, #334155)" }}
              dy={6}
            />

            <YAxis
              stroke="var(--clr-text-muted, #94a3b8)"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "var(--clr-border, #334155)" }}
              dx={-4}
              tickFormatter={(v) => {
                if (Math.abs(v) >= 1000) {
                  return `${(v / 1000).toFixed(1)}k`;
                }
                return String(v);
              }}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Subtle Baseline Reference Line */}
            {showReferenceLines && baseline != null && (
              <ReferenceLine
                y={baseline}
                stroke="#94a3b8"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{
                  value: `Baseline: ${baseline} ${unit}`,
                  position: "insideTopRight",
                  fill: "#94a3b8",
                  fontSize: 10,
                  fontWeight: 600,
                }}
              />
            )}

            {/* Warning Threshold Reference Line */}
            {showReferenceLines && warningThreshold != null && (
              <ReferenceLine
                y={warningThreshold}
                stroke="#f59e0b"
                strokeDasharray="3 3"
                strokeWidth={1.5}
                label={{
                  value: `Warning: ${warningThreshold} ${unit}`,
                  position: "insideTopRight",
                  fill: "#f59e0b",
                  fontSize: 10,
                  fontWeight: 600,
                }}
              />
            )}

            {/* Critical Threshold Reference Line */}
            {showReferenceLines && criticalThreshold != null && (
              <ReferenceLine
                y={criticalThreshold}
                stroke="#ef4444"
                strokeDasharray="3 3"
                strokeWidth={1.5}
                label={{
                  value: `Critical: ${criticalThreshold} ${unit}`,
                  position: "insideTopRight",
                  fill: "#ef4444",
                  fontSize: 10,
                  fontWeight: 600,
                }}
              />
            )}

            <Area
              type="monotone"
              dataKey="displayValue"
              stroke={strokeColor}
              strokeWidth={2.5}
              fill={`url(#${gradientId})`}
              dot={renderCustomDot}
              activeDot={{
                r: 5,
                stroke: strokeColor,
                strokeWidth: 2,
                fill: "#ffffff",
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
