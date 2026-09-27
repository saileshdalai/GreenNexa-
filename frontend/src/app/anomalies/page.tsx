"use client";

import React, { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";
import { api } from "@/lib/api";
import { AnomalyRecord, AnomalyListResponse } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  AlertTriangle,
  Filter,
  RefreshCw,
  CheckCircle,
  XCircle,
  Activity,
  ShieldCheck,
  Zap,
  Eye,
  CheckCheck,
  Flame,
  ArrowUpRight,
} from "lucide-react";
import { calculateOptimalScore, getOptimalScoreColorAndLabel } from "@/lib/scoring";

interface PriorityEngineItem {
  id: string;
  organisation_id: string;
  organisation_name: string;
  module: string;
  block_id: string;
  block_name: string;
  anomaly_type: string;
  current_value: number;
  unit?: string;
  baseline: number;
  warning_threshold: number;
  critical_threshold: number;
  priority_score: number;
  priority_level: string;
  why_priority: string;
  recommended_action: string;
  recommendation_status: string;
  status: string;
  timestamp: string;
}

interface PriorityEngineResponse {
  is_active: boolean;
  active_anomaly_count?: number;
  active_count: number;
  threshold: number;
  message?: string;
  status_message?: string;
  items: PriorityEngineItem[];
  top_priority?: PriorityEngineItem | null;
  optimal_score?: number;
}

function AnomaliesPageContent() {
  const { user, activeOrgId, setActiveOrgId } = useAuth();
  const searchParams = useSearchParams();
  const queryOrg = searchParams.get("org");
  const effectiveOrgId = (user?.role === "SUPER_ADMIN" ? (queryOrg || activeOrgId || user.organisation_id) : user?.organisation_id) || activeOrgId;

  useEffect(() => {
    if (user?.role === "SUPER_ADMIN" && queryOrg && queryOrg !== activeOrgId) {
      setActiveOrgId(queryOrg);
    }
  }, [user, queryOrg, activeOrgId, setActiveOrgId]);

  const { showToast } = useToast();
  const { data: notifData, isAnomalyUnseen, markAsRead, markSingleAnomalyRead } = useNotifications();
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);
  const [priorityData, setPriorityData] = useState<PriorityEngineResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("OPEN");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [sensorFilter, setSensorFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  // Summary of active anomalies for live facility health indicator
  const [activeStats, setActiveStats] = useState<{
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
    score: number;
  }>({
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    total: 0,
    score: 100,
  });

  const loadPriorityData = useCallback(async () => {
    if (!effectiveOrgId) return;
    try {
      const res = await api.get<PriorityEngineResponse>(`/api/v1/anomalies/${effectiveOrgId}/priority`);
      setPriorityData(res);
    } catch {
      setPriorityData(null);
    }
  }, [effectiveOrgId]);

  const loadActiveStats = useCallback(async () => {
    if (!effectiveOrgId) return;
    try {
      const res = await api.get<AnomalyListResponse | AnomalyRecord[]>(`/api/v1/anomalies`, {
        organisation_id: effectiveOrgId,
        limit: 200,
      });
      const items = Array.isArray(res)
        ? res
        : Array.isArray((res as AnomalyListResponse)?.items)
        ? (res as AnomalyListResponse).items
        : [];

      // Active anomalies = OPEN or ACKNOWLEDGED; RESOLVED and DISMISSED excluded
      const activeItems = items.filter(
        (a) => !a.status || a.status === "OPEN" || a.status === "ACKNOWLEDGED"
      );

      const crit = activeItems.filter((a) => a.severity === "CRITICAL").length;
      const high = activeItems.filter((a) => a.severity === "HIGH").length;
      const med = activeItems.filter((a) => a.severity === "MEDIUM").length;
      const low = activeItems.filter((a) => a.severity === "LOW").length;
      const score = calculateOptimalScore(activeItems);

      setActiveStats({
        critical: crit,
        high: high,
        medium: med,
        low: low,
        total: activeItems.length,
        score: score,
      });
    } catch {
      // Keep previous stats
    }
  }, [activeOrgId]);

  const loadAnomalies = useCallback(async () => {
    if (!effectiveOrgId) return;
    setLoading(true);
    try {
      const params: Record<string, any> = { organisation_id: effectiveOrgId, limit: 100 };
      if (statusFilter !== "ALL") params.status = statusFilter;
      if (severityFilter !== "ALL") params.severity = severityFilter;
      if (sensorFilter !== "ALL") params.sensor_type = sensorFilter;

      const res = await api.get<AnomalyListResponse | AnomalyRecord[]>(`/api/v1/anomalies`, params);
      const items = Array.isArray(res)
        ? res
        : Array.isArray((res as AnomalyListResponse)?.items)
        ? (res as AnomalyListResponse).items
        : [];
      setAnomalies(items);
    } catch {
      setAnomalies([]);
    } finally {
      setLoading(false);
    }
  }, [effectiveOrgId, statusFilter, severityFilter, sensorFilter]);

  useEffect(() => {
    loadAnomalies();
    loadActiveStats();
    loadPriorityData();
  }, [loadAnomalies, loadActiveStats, loadPriorityData]);

  useEffect(() => {
    const handleSync = () => {
      loadAnomalies();
      loadActiveStats();
      loadPriorityData();
    };
    window.addEventListener("greennexa_day_changed", handleSync);
    window.addEventListener("greennexa_telemetry_updated", handleSync);
    return () => {
      window.removeEventListener("greennexa_day_changed", handleSync);
      window.removeEventListener("greennexa_telemetry_updated", handleSync);
    };
  }, [loadAnomalies, loadActiveStats, loadPriorityData]);

  const handleUpdateStatus = async (anomalyId: string, newStatus: "RESOLVED" | "DISMISSED") => {
    setActionLoading((prev) => ({ ...prev, [anomalyId]: true }));
    try {
      // Viewing/acting on an anomaly marks it seen without altering lifecycle decoupling
      await markSingleAnomalyRead(anomalyId);
      await api.patch(`/api/v1/anomalies/${anomalyId}`, { status: newStatus });
      showToast(`Anomaly marked as ${newStatus}`, "success");

      // Optimistically update or re-fetch data
      await Promise.all([loadAnomalies(), loadActiveStats(), loadPriorityData()]);

      // Notify other open components (such as dashboard and module block views) to refresh live
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("greennexa_anomaly_updated", { detail: { anomalyId, status: newStatus } }));
        window.dispatchEvent(new Event("greennexa_demo_mode_changed"));
        localStorage.setItem("greennexa_last_anomaly_action", `${anomalyId}:${newStatus}:${Date.now()}`);
      }
    } catch (err: any) {
      showToast(err?.message || `Failed to update anomaly status to ${newStatus}.`, "error");
    } finally {
      setActionLoading((prev) => ({ ...prev, [anomalyId]: false }));
    }
  };

  const handleMarkSeen = async (anomalyId: string) => {
    try {
      await markSingleAnomalyRead(anomalyId);
      showToast("Marked anomaly as seen", "info");
    } catch {
      showToast("Failed to mark anomaly as seen", "error");
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAsRead({ all_unseen: true });
      showToast("All unread notifications marked as read", "success");
    } catch {
      showToast("Failed to mark all notifications as read", "error");
    }
  };

  const safeAnomalies = Array.isArray(anomalies) ? anomalies : [];

  // Health Score styling using common helper
  const { color: healthColor, label: healthLabel } = getOptimalScoreColorAndLabel(activeStats.score);

  return (
    <AppLayout>
      {/* Header Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "20px",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "28px",
              fontWeight: 800,
              display: "flex",
              alignItems: "center",
              gap: "10px",
              margin: 0,
            }}
          >
            <AlertTriangle color="var(--clr-warning)" /> Anomaly Lifecycle & Health Monitor
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", margin: "4px 0 0 0" }}>
            Real-time anomaly lifecycle management, automated threshold deviations, and live facility health impact.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {notifData?.unseen_anomaly_ids?.length > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="btn btn-outline btn-sm"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                borderColor: "var(--clr-primary)",
                color: "var(--clr-primary)",
              }}
              title="Mark all unread operational changes as seen"
              aria-label="Mark all unread operational changes as seen"
            >
              <CheckCheck size={14} />
              <span>Mark All as Read ({notifData.unseen_anomaly_ids.length})</span>
            </button>
          )}

          <button
            onClick={() => {
              loadAnomalies();
              loadActiveStats();
            }}
            className="btn btn-outline btn-sm"
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Facility Health & Active Anomaly Metric Strip */}
      <div
        className="card"
        style={{
          padding: "16px 20px",
          marginBottom: "24px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          borderLeft: `5px solid ${healthColor}`,
          background: "var(--clr-surface-1)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              backgroundColor: `${healthColor}20`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Activity size={24} color={healthColor} />
          </div>
          <div>
            <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
              Optimal Score
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "22px", fontWeight: 800, color: healthColor }}>
                Optimal Score: {activeStats.score}%
              </span>
              <span style={{ fontSize: "11px", fontWeight: 700, color: healthColor }}>
                {healthLabel}
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              backgroundColor: activeStats.total > 0 ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {activeStats.total > 0 ? (
              <AlertTriangle size={24} color="#ef4444" />
            ) : (
              <ShieldCheck size={24} color="#10b981" />
            )}
          </div>
          <div>
            <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
              Active Anomalies
            </div>
            <div style={{ fontSize: "24px", fontWeight: 800, color: activeStats.total > 0 ? "#ef4444" : "#10b981" }}>
              {activeStats.total}
              <span style={{ fontSize: "11px", fontWeight: 500, color: "var(--clr-text-muted)", marginLeft: "8px" }}>
                ({activeStats.critical} crit, {activeStats.high} high, {activeStats.medium} med, {activeStats.low} low)
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              backgroundColor: "rgba(59, 130, 246, 0.15)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Zap size={24} color="#3b82f6" />
          </div>
          <div>
            <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
              Optimal Score Methodology
            </div>
            <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>
              100% baseline minus active anomaly penalties (Crit: -20%, High: -10%, Med: -5%, Low: -2%). Resolving or dismissing immediately restores score.
            </div>
          </div>
        </div>
      </div>

      {/* Priority Engine Escalation Section (Feature 1) */}
      {priorityData && (
        <div
          className="card"
          style={{
            padding: "20px 24px",
            marginBottom: "24px",
            border: priorityData.is_active ? "1px solid rgba(239, 68, 68, 0.45)" : "1px solid var(--clr-border)",
            background: priorityData.is_active
              ? "radial-gradient(ellipse at top right, rgba(239, 68, 68, 0.12), var(--clr-surface-1))"
              : "var(--clr-surface-1)",
            boxShadow: priorityData.is_active ? "0 4px 20px rgba(239, 68, 68, 0.1)" : "none",
            transition: "all 0.3s ease",
          }}
        >
          {/* Priority Engine Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "12px",
              marginBottom: priorityData.is_active ? "18px" : "0",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "10px",
                  backgroundColor: priorityData.is_active ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.15)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {priorityData.is_active ? (
                  <Flame size={22} color="#ef4444" />
                ) : (
                  <ShieldCheck size={22} color="#10b981" />
                )}
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h2 style={{ fontSize: "16px", fontWeight: 800, margin: 0 }}>
                    PRIORITY ENGINE
                  </h2>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 800,
                      padding: "2px 8px",
                      borderRadius: "12px",
                      backgroundColor: priorityData.is_active ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
                      color: priorityData.is_active ? "#ef4444" : "#10b981",
                      border: priorityData.is_active ? "1px solid rgba(239, 68, 68, 0.4)" : "1px solid rgba(16, 185, 129, 0.3)",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <span
                      style={{
                        width: "6px",
                        height: "6px",
                        borderRadius: "50%",
                        backgroundColor: priorityData.is_active ? "#ef4444" : "#10b981",
                      }}
                    />
                    {priorityData.is_active ? "ACTIVE (3+ ACTIVE ANOMALIES)" : "INACTIVE (NORMAL OPERATIONS)"}
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--clr-text-secondary)", margin: "3px 0 0 0" }}>
                  {priorityData.is_active
                    ? `Priority Engine is ACTIVE (${priorityData.active_count} active anomalies). Evaluates risk severity, threshold breach, persistence, and recurrence.`
                    : `Active unresolved anomalies (${priorityData.active_count}) do not reach activation threshold (3). Priority escalation engages when 3+ active anomalies exist.`}
                </p>
              </div>
            </div>

            <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--clr-text-muted)" }}>
              Active Load:{" "}
              <strong style={{ color: priorityData.is_active ? "#ef4444" : "#10b981" }}>
                {priorityData.active_count}
              </strong>{" "}
              / Threshold: &ge;3
            </div>
          </div>

          {/* When active but no high-priority anomaly detected */}
          {priorityData.is_active && priorityData.items.length === 0 && (
            <div
              style={{
                padding: "20px",
                borderRadius: "10px",
                backgroundColor: "var(--clr-surface-2)",
                border: "1px dashed var(--clr-border)",
                textAlign: "center",
                color: "var(--clr-text-secondary)",
                fontSize: "14px",
                fontWeight: 600,
              }}
            >
              {priorityData.status_message || priorityData.message || "No high-priority anomaly detected."}
            </div>
          )}

          {/* Prioritized Urgent Items List (Only rendered when active) */}
          {priorityData.is_active && priorityData.items.length > 0 && (
            <div style={{ display: "grid", gap: "14px" }}>
              {priorityData.items.map((item, idx) => {
                const isCrit = item.priority_level === "P1_CRITICAL";
                const isHigh = item.priority_level === "P2_HIGH";
                const badgeBg = isCrit
                  ? "rgba(239, 68, 68, 0.15)"
                  : isHigh
                  ? "rgba(249, 115, 22, 0.15)"
                  : "rgba(245, 158, 11, 0.15)";
                const badgeClr = isCrit ? "#ef4444" : isHigh ? "#f97316" : "#f59e0b";

                return (
                  <div
                    key={item.id}
                    style={{
                      borderRadius: "10px",
                      border: `1px solid ${isCrit ? "rgba(239, 68, 68, 0.3)" : "var(--clr-border)"}`,
                      backgroundColor: "var(--clr-surface-2)",
                      padding: "14px 18px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                    }}
                  >
                    {/* Top Row */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        flexWrap: "wrap",
                        gap: "8px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 800,
                            padding: "3px 8px",
                            borderRadius: "6px",
                            backgroundColor: badgeBg,
                            color: badgeClr,
                            border: `1px solid ${badgeClr}40`,
                          }}
                        >
                          #{idx + 1} {item.priority_level}
                        </span>
                        {isAnomalyUnseen(item.id) && (
                          <RedDotIndicator size="sm" label="New unread priority anomaly" />
                        )}
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "6px",
                            backgroundColor: "rgba(99, 102, 241, 0.15)",
                            color: "#818cf8",
                          }}
                        >
                          Score: {item.priority_score.toFixed(0)}/100
                        </span>
                        <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-text-primary)" }}>
                          {item.organisation_name} • {item.module.toUpperCase()} • {item.block_name} {item.anomaly_type ? `• ${item.anomaly_type}` : ""}
                        </span>
                      </div>

                      <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </div>
                    </div>

                    {/* Metrics Bar */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                        gap: "8px",
                        background: "var(--clr-surface-1)",
                        padding: "8px 12px",
                        borderRadius: "8px",
                        fontSize: "11px",
                      }}
                    >
                      <div>
                        <span style={{ color: "var(--clr-text-muted)" }}>Current Value: </span>
                        <strong style={{ color: "#ef4444" }}>{item.current_value.toFixed(2)} {item.unit || ""}</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--clr-text-muted)" }}>Baseline: </span>
                        <strong>{item.baseline.toFixed(2)} {item.unit || ""}</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--clr-text-muted)" }}>Warning Thresh: </span>
                        <strong>{item.warning_threshold.toFixed(2)} {item.unit || ""}</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--clr-text-muted)" }}>Critical Thresh: </span>
                        <strong style={{ color: "#ef4444" }}>{item.critical_threshold.toFixed(2)} {item.unit || ""}</strong>
                      </div>
                    </div>

                    {/* Explainable Why Priority & Action */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                      <div
                        style={{
                          backgroundColor: "rgba(239, 68, 68, 0.06)",
                          borderLeft: "3px solid #ef4444",
                          padding: "8px 10px",
                          borderRadius: "4px",
                          fontSize: "12px",
                        }}
                      >
                        <strong style={{ color: "#ef4444", display: "block", marginBottom: "2px" }}>
                          Why Priority:
                        </strong>
                        <span style={{ color: "var(--clr-text-secondary)" }}>{item.why_priority}</span>
                      </div>

                      <div
                        style={{
                          backgroundColor: "rgba(16, 185, 129, 0.06)",
                          borderLeft: "3px solid #10b981",
                          padding: "8px 10px",
                          borderRadius: "4px",
                          fontSize: "12px",
                        }}
                      >
                        <strong style={{ color: "#10b981", display: "block", marginBottom: "2px" }}>
                          Recommended Action ({item.recommendation_status || "OPEN"}):
                        </strong>
                        <span style={{ color: "var(--clr-text-secondary)" }}>{item.recommended_action}</span>
                      </div>
                    </div>

                    {/* Action Bar */}
                    <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "2px" }}>
                      <button
                        onClick={() => handleUpdateStatus(item.id, "RESOLVED")}
                        disabled={actionLoading[item.id]}
                        className="btn btn-sm"
                        style={{
                          backgroundColor: "rgba(16, 185, 129, 0.15)",
                          color: "#10b981",
                          borderColor: "rgba(16, 185, 129, 0.4)",
                          fontSize: "11px",
                          padding: "4px 10px",
                        }}
                      >
                        <CheckCircle size={13} />
                        <span>Resolve Priority</span>
                      </button>
                      <button
                        onClick={() => handleUpdateStatus(item.id, "DISMISSED")}
                        disabled={actionLoading[item.id]}
                        className="btn btn-outline btn-sm"
                        style={{
                          fontSize: "11px",
                          padding: "4px 10px",
                        }}
                      >
                        <XCircle size={13} />
                        <span>Dismiss</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Filter Toolbar */}
      <div
        className="card"
        style={{
          padding: "16px 20px",
          marginBottom: "24px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        {/* Status Lifecycle Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <span style={{ fontSize: "13px", fontWeight: 700, minWidth: "90px", color: "var(--clr-text-primary)" }}>
            Lifecycle Status:
          </span>
          {[
            { key: "OPEN", label: "Open / Active", badgeCount: activeStats.total },
            { key: "RESOLVED", label: "Resolved" },
            { key: "DISMISSED", label: "Dismissed" },
            { key: "ALL", label: "All Records" },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => setStatusFilter(item.key)}
              className={`btn btn-sm ${statusFilter === item.key ? "btn-primary" : "btn-outline"}`}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              <span>{item.label}</span>
              {item.badgeCount !== undefined && item.badgeCount > 0 && (
                <span
                  style={{
                    backgroundColor: statusFilter === item.key ? "#ffffff" : "#ef4444",
                    color: statusFilter === item.key ? "var(--clr-primary)" : "#ffffff",
                    borderRadius: "10px",
                    padding: "1px 6px",
                    fontSize: "11px",
                    fontWeight: 700,
                  }}
                >
                  {item.badgeCount}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Severity and Sensor Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: "24px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Filter size={15} color="var(--clr-text-muted)" />
            <span style={{ fontSize: "13px", fontWeight: 600 }}>Severity:</span>
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
              <button
                key={s}
                onClick={() => setSeverityFilter(s)}
                className={`btn btn-sm ${severityFilter === s ? "btn-secondary" : "btn-outline"}`}
                style={{ fontSize: "12px" }}
              >
                {s}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "13px", fontWeight: 600 }}>Metric:</span>
            {["ALL", "energy", "water", "waste", "temperature", "humidity", "co2"].map((s) => (
              <button
                key={s}
                onClick={() => setSensorFilter(s)}
                className={`btn btn-sm ${sensorFilter === s ? "btn-accent" : "btn-outline"}`}
                style={{ textTransform: "capitalize", fontSize: "12px" }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Anomalies Table */}
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "24px" }}>
            <Skeleton height="40px" style={{ marginBottom: "12px" }} />
            <Skeleton height="40px" style={{ marginBottom: "12px" }} />
            <Skeleton height="40px" />
          </div>
        ) : safeAnomalies.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                textAlign: "left",
                fontSize: "13px",
              }}
            >
              <thead>
                <tr
                  style={{
                    background: "var(--clr-surface-2)",
                    borderBottom: "1px solid var(--clr-border)",
                    color: "var(--clr-text-secondary)",
                  }}
                >
                  <th style={{ padding: "12px 18px" }}>Severity</th>
                  <th style={{ padding: "12px 18px" }}>Status</th>
                  <th style={{ padding: "12px 18px" }}>Metric & Location</th>
                  <th style={{ padding: "12px 18px" }}>Observed</th>
                  <th style={{ padding: "12px 18px" }}>Expected Baseline</th>
                  <th style={{ padding: "12px 18px" }}>Z-Score</th>
                  <th style={{ padding: "12px 18px" }}>Timestamp</th>
                  <th style={{ padding: "12px 18px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {safeAnomalies.map((a) => {
                  const metricName = a.sensor_type || a.metric || "sensor";
                  const blockInfo = a.facility_id || (a.block_id ? `Block ${a.block_id}` : null);
                  const expVal =
                    a.expected_value !== undefined
                      ? a.expected_value
                      : a.expected_min != null && a.expected_max != null
                      ? `${a.expected_min}–${a.expected_max}`
                      : "N/A";
                  const zScore = (a.anomaly_score ?? a.score ?? 0).toFixed(2);
                  const status = (a.status || "OPEN").toUpperCase();
                  const isPending = actionLoading[a.id];
                  const isUnseen = isAnomalyUnseen(a.id);

                  return (
                    <tr
                      key={a.id}
                      style={{
                        borderBottom: "1px solid var(--clr-border-light)",
                        backgroundColor: isUnseen
                          ? "rgba(239, 68, 68, 0.04)"
                          : status === "OPEN"
                          ? "transparent"
                          : "var(--clr-surface-1)",
                        boxShadow: isUnseen ? "inset 3px 0 0 #ef4444" : undefined,
                      }}
                    >
                      {/* Severity */}
                      <td style={{ padding: "12px 18px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <Badge
                            variant={
                              a.severity === "CRITICAL"
                                ? "error"
                                : a.severity === "HIGH"
                                ? "warning"
                                : "neutral"
                            }
                          >
                            {a.severity}
                          </Badge>
                          {isUnseen && (
                            <div style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                              <RedDotIndicator size="sm" label="New unread anomaly" />
                              <span
                                style={{
                                  backgroundColor: "rgba(239, 68, 68, 0.15)",
                                  color: "#ef4444",
                                  fontSize: "10px",
                                  fontWeight: 800,
                                  padding: "1px 6px",
                                  borderRadius: "10px",
                                  border: "1px solid rgba(239, 68, 68, 0.3)",
                                }}
                              >
                                NEW
                              </span>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td style={{ padding: "12px 18px" }}>
                        <Badge
                          variant={
                            status === "OPEN"
                              ? "error"
                              : status === "RESOLVED"
                              ? "success"
                              : status === "DISMISSED"
                              ? "neutral"
                              : "warning"
                          }
                        >
                          {status}
                        </Badge>
                      </td>

                      {/* Metric & Location */}
                      <td style={{ padding: "12px 18px" }}>
                        <div style={{ fontWeight: 700, textTransform: "capitalize" }}>
                          {metricName}
                        </div>
                        {blockInfo && (
                          <div style={{ fontSize: "11px", color: "var(--clr-text-secondary)" }}>
                            {blockInfo}
                          </div>
                        )}
                      </td>

                      {/* Observed Value */}
                      <td style={{ padding: "12px 18px", fontWeight: 700 }}>
                        {a.value} {a.unit || ""}
                      </td>

                      {/* Expected Range */}
                      <td style={{ padding: "12px 18px", color: "var(--clr-text-secondary)" }}>
                        {expVal}
                      </td>

                      {/* Z-Score */}
                      <td style={{ padding: "12px 18px", fontFamily: "monospace" }}>
                        {zScore}
                      </td>

                      {/* Timestamp */}
                      <td
                        style={{
                          padding: "12px 18px",
                          color: "var(--clr-text-muted)",
                          fontSize: "12px",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {new Date(a.timestamp).toLocaleString()}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: "12px 18px", textAlign: "right" }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "flex-end",
                            alignItems: "center",
                            gap: "8px",
                          }}
                        >
                          {isUnseen && (
                            <button
                              onClick={() => handleMarkSeen(a.id)}
                              className="btn btn-outline btn-sm"
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                fontSize: "11px",
                                padding: "4px 8px",
                                color: "#ef4444",
                                borderColor: "rgba(239, 68, 68, 0.4)",
                              }}
                              title="Mark as seen (clears red dot notification without altering lifecycle status)"
                              aria-label="Mark anomaly as seen"
                            >
                              <Eye size={12} />
                              <span>Seen</span>
                            </button>
                          )}

                          {status === "OPEN" || status === "ACKNOWLEDGED" ? (
                            <>
                              <button
                                onClick={() => handleUpdateStatus(a.id, "RESOLVED")}
                                disabled={isPending}
                                className="btn btn-primary btn-sm"
                                style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}
                                title="Resolve this anomaly and restore health score"
                              >
                                <CheckCircle size={13} />
                                <span>{isPending ? "..." : "Resolve"}</span>
                              </button>
                              <button
                                onClick={() => handleUpdateStatus(a.id, "DISMISSED")}
                                disabled={isPending}
                                className="btn btn-outline btn-sm"
                                style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}
                                title="Dismiss false positive anomaly"
                              >
                                <XCircle size={13} />
                                <span>{isPending ? "..." : "Dismiss"}</span>
                              </button>
                            </>
                          ) : status === "RESOLVED" ? (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                color: "var(--clr-success, #10b981)",
                                fontSize: "12px",
                                fontWeight: 600,
                              }}
                            >
                              <CheckCircle size={14} />
                              <span>Resolved</span>
                            </span>
                          ) : (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                color: "var(--clr-text-muted)",
                                fontSize: "12px",
                              }}
                            >
                              <XCircle size={14} />
                              <span>Dismissed</span>
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title={`No ${statusFilter.toLowerCase()} anomalies found`}
            description={
              statusFilter === "OPEN"
                ? "All facility sensors are operating within optimal parameters and baseline thresholds."
                : `No anomaly records currently match status filter '${statusFilter}'.`
            }
          />
        )}
      </div>
    </AppLayout>
  );
}

export default function AnomaliesPage() {
  return (
    <Suspense
      fallback={
        <AppLayout>
          <div style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
            Loading anomaly intelligence...
          </div>
        </AppLayout>
      }
    >
      <AnomaliesPageContent />
    </Suspense>
  );
}
