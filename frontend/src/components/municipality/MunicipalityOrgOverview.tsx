"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DashboardKPIs, AnomalyRecord, AIRecommendation, AnomalyListResponse, RecommendationListResponse } from "@/types";
import { DataSourceBadge } from "@/components/ui/DataSourceBadge";
import { CardSkeleton } from "@/components/ui/Skeleton";
import {
  Building2,
  X,
  Zap,
  Droplet,
  Trash2,
  Wind,
  AlertTriangle,
  Lightbulb,
  ShieldCheck,
  CheckCircle2,
  Clock,
  ExternalLink,
} from "lucide-react";

interface MunicipalityOrgOverviewProps {
  orgId: string;
  orgName?: string;
  isOpen: boolean;
  onClose: () => void;
}

export const MunicipalityOrgOverview: React.FC<MunicipalityOrgOverviewProps> = ({
  orgId,
  orgName,
  isOpen,
  onClose,
}) => {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !orgId) return;

    const loadOrgData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [kpiRes, anomalyRes, recRes] = await Promise.allSettled([
          api.get<DashboardKPIs>(`/api/v1/dashboard/${orgId}`),
          api.get<AnomalyListResponse | AnomalyRecord[]>(`/api/v1/anomalies`, {
            organisation_id: orgId,
            limit: 5,
            status: "OPEN",
          }),
          api.get<RecommendationListResponse | AIRecommendation[]>(`/api/v1/recommendations`, {
            organisation_id: orgId,
            status: "OPEN",
          }),
        ]);

        if (kpiRes.status === "fulfilled") {
          setKpis(kpiRes.value);
        } else {
          setError("Unable to load overview telemetry for this organisation.");
        }

        if (anomalyRes.status === "fulfilled" && anomalyRes.value) {
          const val = anomalyRes.value;
          const list = Array.isArray(val)
            ? val
            : Array.isArray((val as AnomalyListResponse)?.items)
            ? (val as AnomalyListResponse).items
            : [];
          setAnomalies(list);
        }

        if (recRes.status === "fulfilled" && recRes.value) {
          const val = recRes.value;
          const list = Array.isArray(val)
            ? val
            : Array.isArray((val as RecommendationListResponse)?.items)
            ? (val as RecommendationListResponse).items
            : [];
          setRecommendations(list.filter((r) => r.status === "OPEN" || r.status === "ACTIVE").slice(0, 3));
        }
      } catch (err: any) {
        setError(err.message || "Failed to load organisation data.");
      } finally {
        setLoading(false);
      }
    };

    loadOrgData();
  }, [isOpen, orgId]);

  if (!isOpen) return null;

  const energyKpi = kpis?.kpis?.energy;
  const waterKpi = kpis?.kpis?.water;
  const wasteKpi = kpis?.kpis?.waste;
  const aqiKpi = kpis?.kpis?.air_quality;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.7)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: "var(--clr-surface-1)",
          border: "1px solid var(--clr-border)",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "800px",
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--clr-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--clr-surface-2)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "rgba(2, 132, 199, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Building2 size={22} color="#0284c7" />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h2 style={{ fontSize: "18px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
                  {orgName || kpis?.organisation_name || orgId}
                </h2>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    color: "#0284c7",
                    background: "rgba(2, 132, 199, 0.12)",
                    border: "1px solid rgba(2, 132, 199, 0.3)",
                    padding: "2px 8px",
                    borderRadius: "12px",
                  }}
                >
                  READ-ONLY OVERSIGHT
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "2px" }}>
                Organisation ID: {orgId} · Civic Sustainability Oversight
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--clr-text-muted)",
              cursor: "pointer",
              padding: "6px",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
          {loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : error ? (
            <div
              style={{
                padding: "20px",
                textAlign: "center",
                color: "#ef4444",
                background: "rgba(239, 68, 68, 0.08)",
                borderRadius: "10px",
              }}
            >
              {error}
            </div>
          ) : (
            <>
              {/* Top Operational Metrics */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                  gap: "12px",
                }}
              >
                {/* Energy */}
                <div
                  style={{
                    background: "var(--clr-surface-2)",
                    border: "1px solid var(--clr-border)",
                    borderRadius: "12px",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#f59e0b", marginBottom: "8px" }}>
                    <Zap size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 700 }}>Energy</span>
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                    {energyKpi?.latest_value != null ? `${energyKpi.latest_value.toLocaleString()} ${energyKpi.unit || "kWh"}` : "—"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
                    Avg: {energyKpi?.average != null ? `${energyKpi.average} ${energyKpi.unit || "kWh"}` : "—"}
                  </div>
                </div>

                {/* Water */}
                <div
                  style={{
                    background: "var(--clr-surface-2)",
                    border: "1px solid var(--clr-border)",
                    borderRadius: "12px",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#38bdf8", marginBottom: "8px" }}>
                    <Droplet size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 700 }}>Water</span>
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                    {waterKpi?.latest_value != null ? `${waterKpi.latest_value.toLocaleString()} ${waterKpi.unit || "L"}` : "—"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
                    Avg: {waterKpi?.average != null ? `${waterKpi.average} ${waterKpi.unit || "L"}` : "—"}
                  </div>
                </div>

                {/* Waste */}
                <div
                  style={{
                    background: "var(--clr-surface-2)",
                    border: "1px solid var(--clr-border)",
                    borderRadius: "12px",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#10b981", marginBottom: "8px" }}>
                    <Trash2 size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 700 }}>Waste Fill</span>
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                    {wasteKpi?.latest_value != null ? `${wasteKpi.latest_value} ${wasteKpi.unit || "%"}` : "—"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
                    Max: {wasteKpi?.maximum != null ? `${wasteKpi.maximum} ${wasteKpi.unit || "%"}` : "—"}
                  </div>
                </div>

                {/* Air Quality */}
                <div
                  style={{
                    background: "var(--clr-surface-2)",
                    border: "1px solid var(--clr-border)",
                    borderRadius: "12px",
                    padding: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#a78bfa", marginBottom: "8px" }}>
                    <Wind size={16} />
                    <span style={{ fontSize: "12px", fontWeight: 700 }}>Air Quality</span>
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                    {aqiKpi?.latest_value != null ? `${aqiKpi.latest_value} AQI` : "—"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
                    Status: {aqiKpi?.latest_value != null && aqiKpi.latest_value > 100 ? "Moderate" : "Good"}
                  </div>
                </div>
              </div>

              {/* Active Anomalies & Recommendations Row */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
                {/* Anomalies Panel */}
                <div
                  style={{
                    background: "var(--clr-surface-2)",
                    border: "1px solid var(--clr-border)",
                    borderRadius: "12px",
                    padding: "18px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "14px", color: "var(--clr-text-primary)" }}>
                      <AlertTriangle size={16} color="#f59e0b" />
                      Active Anomalies ({anomalies.length})
                    </div>
                  </div>
                  {anomalies.length === 0 ? (
                    <div style={{ fontSize: "13px", color: "#10b981", textAlign: "center", padding: "16px 0" }}>
                      ✓ No active anomalies detected
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {anomalies.map((a) => {
                        const sev = (a as any).severity || "NORMAL";
                        const isCrit = sev === "CRITICAL";
                        return (
                          <div
                            key={a.id}
                            style={{
                              padding: "10px 12px",
                              borderRadius: "8px",
                              background: isCrit ? "rgba(239, 68, 68, 0.08)" : "rgba(245, 158, 11, 0.08)",
                              border: `1px solid ${isCrit ? "rgba(239, 68, 68, 0.25)" : "rgba(245, 158, 11, 0.25)"}`,
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{ fontSize: "12px", fontWeight: 700, color: isCrit ? "#ef4444" : "#f59e0b" }}>
                                {sev} — {(a as any).metric || (a as any).sensor_type}
                              </span>
                              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>
                                Val: {a.value}
                              </span>
                            </div>
                            <div style={{ fontSize: "11px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>
                              {(a as any).reason || "Threshold exceeded"}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* AI Recommendations Panel */}
                <div
                  style={{
                    background: "var(--clr-surface-2)",
                    border: "1px solid var(--clr-border)",
                    borderRadius: "12px",
                    padding: "18px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "14px", color: "var(--clr-text-primary)" }}>
                      <Lightbulb size={16} color="#a78bfa" />
                      AI Recommendations ({recommendations.length})
                    </div>
                  </div>
                  {recommendations.length === 0 ? (
                    <div style={{ fontSize: "13px", color: "var(--clr-text-muted)", textAlign: "center", padding: "16px 0" }}>
                      No open recommendations
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {recommendations.map((r) => (
                        <div
                          key={r.id}
                          style={{
                            padding: "10px 12px",
                            borderRadius: "8px",
                            background: "rgba(167, 139, 250, 0.08)",
                            border: "1px solid rgba(167, 139, 250, 0.2)",
                          }}
                        >
                          <div style={{ fontSize: "12px", fontWeight: 700, color: "#a78bfa" }}>
                            {r.metric || "Optimization"} · {r.priority || "MEDIUM"}
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--clr-text-secondary)", marginTop: "2px", lineHeight: 1.4 }}>
                            {r.summary || "Follow recommended civic protocols."}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Note / Read Only Disclaimer */}
              <div
                style={{
                  fontSize: "12px",
                  color: "var(--clr-text-muted)",
                  background: "var(--clr-surface-2)",
                  padding: "12px 16px",
                  borderRadius: "8px",
                  border: "1px dashed var(--clr-border)",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <ShieldCheck size={16} color="#0284c7" />
                <span>
                  This overview is provided as municipal oversight intelligence. Internal block-level routing and administrative controls are restricted to the organisation's administrators.
                </span>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--clr-border)",
            display: "flex",
            justifyContent: "flex-end",
            background: "var(--clr-surface-2)",
          }}
        >
          <button onClick={onClose} className="btn btn-outline btn-sm">
            Close Overview
          </button>
        </div>
      </div>
    </div>
  );
};
