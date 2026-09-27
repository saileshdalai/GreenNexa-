"use client";

import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/EmptyState";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { useNotifications } from "@/context/NotificationContext";
import { ArrowLeft, MapPin, RefreshCw, AlertTriangle, Activity, Lightbulb, TrendingUp } from "lucide-react";

interface WardDetailMetric {
  sensor_type: string;
  label: string;
  latest_value?: number | null;
  unit?: string | null;
  status: string;
  timestamp?: string | null;
  has_data: boolean;
  is_anomaly: boolean;
  anomaly_severity?: string | null;
}

interface WardAnomalyItem {
  id: string;
  metric: string;
  severity: string;
  reason?: string | null;
  timestamp?: string | null;
  trigger_value?: number | null;
  expected_min?: number | null;
  expected_max?: number | null;
  anomaly_score?: number | null;
  unit?: string | null;
}

interface WardRecommendationItem {
  id: string;
  anomaly_id: string;
  metric: string;
  severity: string;
  priority: string;
  status: string;
  facility_id?: string | null;
  summary?: string | null;
  possible_causes?: string[];
  recommended_actions?: string[];
  current_value?: number | null;
  expected_range_min?: number | null;
  expected_range_max?: number | null;
  created_at?: string | null;
}

interface WardForecastPoint {
  timestamp: string;
  predicted_value: number;
  lower_bound?: number | null;
  upper_bound?: number | null;
}

interface WardForecastItem {
  sensor_type: string;
  label: string;
  current_value?: number | null;
  unit?: string | null;
  horizon?: string;
  is_available: boolean;
  points?: WardForecastPoint[];
  message?: string | null;
}

interface WardDetailPayload {
  ward?: {
    id: string;
    municipality_id: string;
    ward_number: string;
    ward_name: string;
    zone?: string | null;
    population?: number | null;
    area_sq_km?: number | null;
    is_active: boolean;
  };
  has_data?: boolean;
  metrics?: Record<string, WardDetailMetric>;
  anomalies?: WardAnomalyItem[];
  recommendations?: WardRecommendationItem[];
  forecasts?: WardForecastItem[];
  message?: string;
}

function WardDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const wardId = (params?.ward_id as string) || "";
  const { user, activeOrgId, setActiveOrgId } = useAuth();
  const queryOrg = searchParams.get("org");

  const effectiveOrgId = React.useMemo(() => {
    if (user?.role === "SUPER_ADMIN") return queryOrg || activeOrgId || user.organisation_id || "";
    return user?.organisation_id || "";
  }, [user, activeOrgId, queryOrg]);

  // Synchronize activeOrgId if provided via query param
  useEffect(() => {
    if (queryOrg && queryOrg !== activeOrgId && setActiveOrgId) {
      setActiveOrgId(queryOrg);
    }
  }, [queryOrg, activeOrgId, setActiveOrgId]);

  const { data: notifData, markAsRead } = useNotifications();

  const [data, setData] = useState<WardDetailPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadWard = async () => {
    if (!effectiveOrgId || !wardId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<WardDetailPayload>(`/api/v1/organisations/${effectiveOrgId}/wards/${wardId}`);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load ward detail.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWard();
  }, [effectiveOrgId, wardId]);

  const ward = data?.ward;
  const metrics = data?.metrics || {};
  const anomalies = data?.anomalies || [];
  const recommendations = data?.recommendations || [];
  const forecasts = data?.forecasts || [];

  const backHref = effectiveOrgId ? `/dashboard?org=${encodeURIComponent(effectiveOrgId)}` : "/dashboard";

  return (
    <AppLayout>
      <div style={{ marginBottom: "24px" }}>
        <Link
          id="back-to-dashboard-link"
          href={backHref}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "13px",
            color: "var(--clr-primary)",
            fontWeight: 600,
            textDecoration: "none",
            marginBottom: "12px",
          }}
        >
          <ArrowLeft size={16} /> Back to Municipality Dashboard
        </Link>

        <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "20px" }}>
          <div style={{ padding: "12px", borderRadius: "12px", background: "var(--clr-surface-2)", border: "1px solid var(--clr-border)" }}>
            <MapPin size={22} color="var(--clr-primary)" />
          </div>
          <div>
            <h1 style={{ fontSize: "26px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
              {ward?.ward_name || "Ward Detail"}
            </h1>
            <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", margin: "4px 0 0 0" }}>
              Ward {ward?.ward_number || wardId}{ward?.zone ? ` · ${ward.zone}` : ""}{ward?.municipality_id ? ` · ${ward.municipality_id}` : ""}
            </p>
          </div>
          <button
            onClick={loadWard}
            className="btn btn-outline btn-sm"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px", marginLeft: "auto" }}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            Refresh
          </button>
        </div>

        {error && (
          <div style={{ padding: "16px", borderRadius: "12px", background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#fca5a5", marginBottom: "24px", fontSize: "14px" }}>
            {error}
          </div>
        )}
      </div>

      {loading ? (
        <div style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", display: "grid", gap: "16px" }}>
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : !ward ? (
        <EmptyState icon={<MapPin size={32} />} title="Ward not found" description="This ward may have been deactivated or belongs to another municipality." />
      ) : !data?.has_data && Object.keys(metrics).length === 0 ? (
        <div>
          <div className="card" style={{ padding: "24px" }}>
            <EmptyState
              title={data?.message || "No civic telemetry data for this ward yet"}
              description={"Ward-level readings appear here once the simulator or ward sensors submit data mapped to this ward."}
            />
          </div>
          {anomalies.length > 0 && (
            <div className="card" style={{ padding: "24px", marginTop: "20px" }}>
              <h2 style={{ fontSize: "16px", fontWeight: 800, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px", color: "var(--clr-text-primary)" }}>
                <AlertTriangle size={18} color="#f59e0b" /> Ward Anomalies
              </h2>
              <WardAnomalyList anomalies={anomalies} />
            </div>
          )}
          <WardForecastSection forecasts={forecasts} />
          <WardRecommendationSection recommendations={recommendations} />
        </div>
      ) : (
        <div>
          <h2 style={{ fontSize: "16px", fontWeight: 800, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px", color: "var(--clr-text-primary)" }}>
            <Activity size={18} color="var(--clr-primary)" /> Civic Telemetry
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px", marginBottom: "20px" }}>
            {Object.values(metrics).map((m) => {
              const valNum = m.latest_value;
              return (
                <div key={m.sensor_type} className="card" style={{ padding: "18px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                    <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-text-secondary)" }}>{m.label || m.sensor_type}</span>
                    <span
                      style={{
                        fontSize: "10px", fontWeight: 800, padding: "2px 8px", borderRadius: "12px",
                        background: m.status === "ONLINE" ? "rgba(52,211,153,0.15)" : m.status === "OFFLINE" ? "rgba(245,158,11,0.15)" : "rgba(148,163,184,0.15)",
                        color: m.status === "ONLINE" ? "#34d399" : m.status === "OFFLINE" ? "#fbbf24" : "var(--clr-text-muted)",
                      }}
                    >
                      {m.status}
                    </span>
                  </div>
                  <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--clr-text-muted)", marginBottom: "4px" }}>
                    Current Value
                  </div>
                  <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                    {typeof valNum === "number" ? valNum.toLocaleString(undefined, { maximumFractionDigits: 1 }) : "—"}
                    {m.unit ? <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--clr-text-muted)" }}> {m.unit}</span> : null}
                  </div>
                  {m.is_anomaly && (
                    <div style={{ marginTop: "8px", fontSize: "11px", fontWeight: 700, color: "#ef4444" }}>
                      ⚠ Active Anomaly ({m.anomaly_severity || "ANOMALY"})
                    </div>
                  )}
                  {!m.has_data && (
                    <div style={{ marginTop: "8px", fontSize: "11px", color: "var(--clr-text-muted)" }}>No data collected yet.</div>
                  )}
                </div>
              );
            })}
          </div>

          <h2 style={{ fontSize: "16px", fontWeight: 800, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px", color: "var(--clr-text-primary)" }}>
            <AlertTriangle size={18} color="#f59e0b" /> Ward Anomalies
          </h2>
          {anomalies.length > 0 ? (
            <div className="card" style={{ padding: "24px" }}>
              <WardAnomalyList anomalies={anomalies} metrics={metrics} />
            </div>
          ) : (
            <EmptyState title="No ward anomalies" description="All ward telemetry is within normal ranges." />
          )}

          <WardForecastSection forecasts={forecasts} />
          <WardRecommendationSection recommendations={recommendations} />
        </div>
      )}
    </AppLayout>
  );
}

function WardAnomalyList({ anomalies, metrics }: { anomalies: WardAnomalyItem[]; metrics?: Record<string, WardDetailMetric> }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      {anomalies.map((a) => {
        const unit = a.unit || (a.metric === "waste" ? "%" : "");
        const triggerValStr = a.trigger_value != null ? `${Number(a.trigger_value).toFixed(1)}${unit}` : null;
        const currentMetric = metrics?.[a.metric];
        const currentMetricVal = currentMetric?.latest_value;
        const currentMetricValStr = currentMetricVal != null ? `${Number(currentMetricVal).toFixed(1)}${unit}` : null;
        return (
          <div
            key={a.id}
            data-testid={`anomaly-item-${a.metric}`}
            style={{
              padding: "14px 16px",
              borderRadius: "10px",
              background: "var(--clr-surface-2)",
              border: "1px solid var(--clr-border)",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "14px", fontWeight: 700, textTransform: "capitalize", color: "var(--clr-text-primary)" }}>
                  {a.metric} Anomaly Event
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 800,
                    padding: "2px 8px",
                    borderRadius: "12px",
                    background: a.severity === "CRITICAL" || a.severity === "HIGH" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)",
                    color: a.severity === "CRITICAL" || a.severity === "HIGH" ? "#f87171" : "#fbbf24",
                  }}
                >
                  {a.severity}
                </span>
              </div>
              {a.timestamp && (
                <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>
                  Event Triggered: {new Date(a.timestamp).toLocaleString()}
                </span>
              )}
            </div>

            {a.reason && (
              <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", lineHeight: 1.4 }}>
                {a.reason}
              </div>
            )}

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "16px",
                padding: "8px 12px",
                borderRadius: "8px",
                background: "var(--clr-surface-1)",
                fontSize: "12px",
              }}
            >
              {triggerValStr && (
                <div>
                  <span style={{ color: "var(--clr-text-muted)" }}>Anomaly Trigger Value: </span>
                  <strong style={{ color: "#ef4444" }}>{triggerValStr}</strong>
                </div>
              )}
              {currentMetricValStr && (
                <div>
                  <span style={{ color: "var(--clr-text-muted)" }}>Current Value: </span>
                  <strong style={{ color: "var(--clr-text-primary)" }}>{currentMetricValStr}</strong>
                </div>
              )}
              {a.expected_min != null && a.expected_max != null && (
                <div>
                  <span style={{ color: "var(--clr-text-muted)" }}>Expected Baseline Range: </span>
                  <span style={{ color: "var(--clr-text-secondary)", fontWeight: 600 }}>
                    {a.expected_min} – {a.expected_max}{unit}
                  </span>
                </div>
              )}
              {a.anomaly_score != null && (
                <div>
                  <span style={{ color: "var(--clr-text-muted)" }}>Anomaly Score: </span>
                  <span style={{ color: "var(--clr-text-secondary)", fontWeight: 600 }}>
                    {(a.anomaly_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function WardForecastSection({ forecasts }: { forecasts: WardForecastItem[] }) {
  if (!forecasts || forecasts.length === 0) return null;
  return (
    <div style={{ marginTop: "20px" }}>
      <h2 style={{ fontSize: "16px", fontWeight: 800, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px", color: "var(--clr-text-primary)" }}>
        <TrendingUp size={18} color="var(--clr-primary)" /> Ward Forecast Estimates
      </h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "14px" }}>
        {forecasts.map((f) => (
          <div key={f.sensor_type} className="card" style={{ padding: "18px" }}>
            <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-text-secondary)", marginBottom: "8px" }}>
              {f.label || f.sensor_type}
              {f.is_available && f.current_value != null && (
                <span style={{ marginLeft: "8px", fontSize: "12px", fontWeight: 600, color: "var(--clr-text-muted)" }}>
                  Now: {Number(f.current_value).toLocaleString(undefined, { maximumFractionDigits: 1 })}{f.unit ? f.unit : ""}
                </span>
              )}
            </div>
            {f.is_available && f.points && f.points.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {f.points.map((p) => (
                  <div key={p.timestamp} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12px" }}>
                    <span style={{ color: "var(--clr-text-muted)" }}>{new Date(p.timestamp).toLocaleString()}</span>
                    <span style={{ fontWeight: 700, color: "var(--clr-text-primary)" }}>
                      {Number(p.predicted_value).toLocaleString(undefined, { maximumFractionDigits: 1 })}
                      {f.unit ? f.unit : ""}
                    </span>
                  </div>
                ))}
                <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "4px" }}>{f.message}</div>
              </div>
            ) : (
              <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", fontStyle: "italic" }}>
                {f.message || "Forecast unavailable for this metric."}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function WardRecommendationSection({ recommendations }: { recommendations: WardRecommendationItem[] }) {
  if (!recommendations || recommendations.length === 0) return null;
  return (
    <div className="card" style={{ padding: "24px", marginTop: "20px" }}>
      <h2 style={{ fontSize: "16px", fontWeight: 800, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px", color: "var(--clr-text-primary)" }}>
        <Lightbulb size={18} color="#a78bfa" /> AI Recommendations
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {recommendations.map((rec) => (
          <div key={rec.id} style={{ padding: "12px 14px", borderRadius: "10px", background: "var(--clr-surface-2)", border: "1px solid rgba(167,139,250,0.25)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <span style={{ fontSize: "12px", fontWeight: 700, textTransform: "capitalize", color: "#a78bfa" }}>
                {(rec.metric || "General")} Recommendation
              </span>
              <span style={{ fontSize: "10px", fontWeight: 800, padding: "2px 8px", borderRadius: "12px", background: rec.severity === "CRITICAL" || rec.severity === "HIGH" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)", color: rec.severity === "CRITICAL" || rec.severity === "HIGH" ? "#f87171" : "#fbbf24" }}>
                {rec.severity}
              </span>
            </div>
            {rec.summary && <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", lineHeight: 1.5, marginBottom: "6px" }}>{rec.summary}</div>}
            {rec.recommended_actions && rec.recommended_actions.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "6px" }}>
                {rec.recommended_actions.map((action, i) => (
                  <div key={i} style={{ fontSize: "12px", color: "var(--clr-text-muted)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ color: "#a78bfa" }}>•</span> {action}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function WardDetailPageWrapper() {
  return (
    <React.Suspense fallback={<div style={{ padding: "2rem", color: "var(--clr-text-secondary)" }}>Loading Ward...</div>}>
      <WardDetailPage />
    </React.Suspense>
  );
}