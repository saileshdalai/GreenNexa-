"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";
import { api } from "@/lib/api";
import {
  ModuleOverallResponse,
  ModuleBlockDetailResponse,
  PredictionRowItem,
  BlockComparisonItem,
  TrendPointItem,
} from "@/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { TimeSeriesWaveform } from "@/components/ui/TimeSeriesWaveform";
import {
  ArrowLeft,
  Activity,
  Zap,
  Droplet,
  Trash2,
  Thermometer,
  ShieldCheck,
  Cpu,
  RefreshCw,
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  TrendingUp,
  BarChart3,
  Layers,
} from "lucide-react";

function ModuleDetailContent() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryOrg = searchParams.get("org");
  const { user, activeOrgId, setActiveOrgId, currentOrg, organisations = [] } = useAuth();

  const effectiveOrgId = React.useMemo(() => {
    if (user?.role === "SUPER_ADMIN") {
      return queryOrg || activeOrgId || user.organisation_id || (organisations.length > 0 ? organisations[0].id : "ORG-00001");
    }
    return user?.organisation_id || null;
  }, [user, activeOrgId, queryOrg, organisations]);

  useEffect(() => {
    if (user?.role === "SUPER_ADMIN" && queryOrg && queryOrg !== activeOrgId) {
      setActiveOrgId(queryOrg);
    }
  }, [user, queryOrg, activeOrgId, setActiveOrgId]);

  const moduleId = (params.module_id as string) || "energy";
  const { isBlockUnread, isModuleUnread, markAsRead } = useNotifications();
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [period, setPeriod] = useState<string>("24h");

  const [overallData, setOverallData] = useState<ModuleOverallResponse | null>(null);
  const [blockData, setBlockData] = useState<ModuleBlockDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async (silent = false) => {
    if (!effectiveOrgId) return;
    if (!silent) setLoading(true);
    setError(null);
    try {
      if (selectedBlockId === null) {
        const res = await api.get<ModuleOverallResponse>(
          `/api/v1/dashboard/${effectiveOrgId}/modules/${moduleId}/overall?period=${period}`
        );
        setOverallData(res);
        setBlockData(null);
      } else {
        const [ovRes, blkRes] = await Promise.all([
          api.get<ModuleOverallResponse>(
            `/api/v1/dashboard/${effectiveOrgId}/modules/${moduleId}/overall?period=${period}`
          ),
          api.get<ModuleBlockDetailResponse>(
            `/api/v1/dashboard/${effectiveOrgId}/modules/${moduleId}/block/${selectedBlockId}?period=${period}`
          ),
        ]);
        setOverallData(ovRes);
        setBlockData(blkRes);
      }
    } catch (err: any) {
      if (!silent) setError(err.message || "Failed to load module intelligence.");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  const handleBlockAnomalyAction = async (anomalyId: string, newStatus: "RESOLVED" | "DISMISSED") => {
    setActionLoading((prev) => ({ ...prev, [anomalyId]: true }));
    try {
      await api.patch(`/api/v1/anomalies/${anomalyId}`, { status: newStatus });
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("greennexa_anomaly_updated", { detail: { anomalyId, status: newStatus } }));
        window.dispatchEvent(new Event("greennexa_demo_mode_changed"));
        localStorage.setItem("greennexa_last_anomaly_action", `${anomalyId}:${newStatus}:${Date.now()}`);
      }
      await loadData(true);
    } catch (err: any) {
      console.error(`Failed to update anomaly status to ${newStatus}:`, err);
    } finally {
      setActionLoading((prev) => ({ ...prev, [anomalyId]: false }));
    }
  };

  useEffect(() => {
    loadData();

    // 15-second polling for live updates
    const pollInterval = setInterval(() => {
      loadData(true);
    }, 15000);

    const handleSync = () => {
      loadData(true);
    };

    window.addEventListener("greennexa_anomaly_updated", handleSync);
    window.addEventListener("greennexa_demo_mode_changed", handleSync);
    window.addEventListener("storage", handleSync);
    window.addEventListener("focus", handleSync);

    return () => {
      clearInterval(pollInterval);
      window.removeEventListener("greennexa_anomaly_updated", handleSync);
      window.removeEventListener("greennexa_demo_mode_changed", handleSync);
      window.removeEventListener("storage", handleSync);
      window.removeEventListener("focus", handleSync);
    };
  }, [effectiveOrgId, moduleId, selectedBlockId, period]);

  const getModuleIcon = (mod: string) => {
    switch (mod) {
      case "energy":
        return <Zap size={24} color="#f59e0b" />;
      case "water":
        return <Droplet size={24} color="#3b82f6" />;
      case "waste":
        return <Trash2 size={24} color="#10b981" />;
      case "temperature":
      case "climate":
        return <Thermometer size={24} color="#ef4444" />;
      case "assets":
        return <Cpu size={24} color="#14b8a6" />;
      case "safety":
        return <ShieldCheck size={24} color="#ef4444" />;
      default:
        return <Activity size={24} color="#a855f7" />;
    }
  };

  const getStatusBadge = (st: string) => {
    if (st === "Critical") return <Badge variant="error">CRITICAL</Badge>;
    if (st === "Warning") return <Badge variant="warning">WARNING</Badge>;
    return <Badge variant="success">OPTIMAL</Badge>;
  };

  const isMunicipalityOrg =
    (overallData as any)?.organisation_type?.toUpperCase() === "MUNICIPALITY" ||
    overallData?.organisation_name?.toLowerCase().includes("municipality") ||
    overallData?.organisation_name?.toLowerCase().includes("corporation") ||
    currentOrg?.org_type === "MUNICIPALITY";
  const backLabel = isMunicipalityOrg ? "Back to Municipality Dashboard" : "Back to Facility Dashboard";
  const backHref = effectiveOrgId ? `/dashboard?org=${encodeURIComponent(effectiveOrgId)}` : "/dashboard";

  return (
    <AppLayout>
      {/* Navigation Header */}
      <div style={{ marginBottom: "24px" }}>
        <Link
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
          <ArrowLeft size={16} /> {backLabel}
        </Link>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <div style={{ padding: "12px", borderRadius: "12px", background: "var(--clr-surface-2)", border: "1px solid var(--clr-border)" }}>
              {getModuleIcon(moduleId)}
            </div>
            <div>
              <h1 style={{ fontSize: "26px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
                {overallData?.module_title || moduleId.toUpperCase()} Intelligence
              </h1>
              <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", margin: "4px 0 0 0" }}>
                Organisation → {overallData?.organisation_name || activeOrgId} → {selectedBlockId ? blockData?.block_name : "Overall Facility View"}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Time Range:</span>
              <select
                className="form-input"
                style={{ padding: "6px 12px", fontSize: "13px" }}
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              >
                <option value="1h">1 Hour</option>
                <option value="6h">6 Hours</option>
                <option value="24h">24 Hours (Today)</option>
                <option value="7d">7 Days</option>
                <option value="30d">30 Days</option>
              </select>
            </div>

            <button onClick={() => loadData(false)} className="btn btn-outline btn-sm" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ padding: "16px", borderRadius: "12px", background: "rgba(239, 68, 68, 0.15)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#fca5a5", marginBottom: "24px" }}>
          {error}
        </div>
      )}

      {/* Location / Scope Selector Bar */}
      <div className="card" style={{ padding: "16px 20px", marginBottom: "28px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Layers size={18} color="var(--clr-primary)" />
            <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-text-primary)" }}>
              {moduleId === "air_quality"
                ? "Air Quality Monitoring Scope:"
                : moduleId === "climate"
                ? "Climate & Environment Scope:"
                : moduleId === "traffic"
                ? "Traffic Monitoring Location:"
                : moduleId === "parking"
                ? "Parking Area / Zone:"
                : moduleId === "safety"
                ? "Safety Incident / Zone:"
                : "Facility Block Selector:"}
            </span>
          </div>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <button
              onClick={() => {
                setSelectedBlockId(null);
                if (isModuleUnread(moduleId)) {
                  markAsRead({ metric: moduleId });
                }
              }}
              className={`btn btn-sm ${selectedBlockId === null ? "btn-primary" : "btn-outline"}`}
              style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: "6px" }}
            >
              <span>[ Overall ]</span>
              {isModuleUnread(moduleId) && (
                <RedDotIndicator
                  size="sm"
                  label={`${moduleId} — new unseen activity`}
                  style={{ marginLeft: "4px" }}
                />
              )}
            </button>

            {overallData?.block_comparison && overallData.block_comparison.length > 0 ? (
              overallData.block_comparison.map((blk) => {
                const isSelected = selectedBlockId === blk.block_id;
                const hasUnread = isBlockUnread(blk.block_id, moduleId);
                return (
                  <button
                    key={blk.block_id}
                    onClick={() => {
                      setSelectedBlockId(blk.block_id);
                      if (hasUnread) {
                        markAsRead({ metric: moduleId, block_id: blk.block_id });
                      }
                    }}
                    className={`btn btn-sm ${isSelected ? "btn-primary" : "btn-outline"}`}
                    style={{ display: "flex", alignItems: "center", gap: "6px", position: "relative" }}
                  >
                    <span>{blk.block_name}</span>
                    {hasUnread ? (
                      <RedDotIndicator
                        size="sm"
                        label={`${blk.block_name} — new unseen activity`}
                        style={{ marginLeft: "4px" }}
                      />
                    ) : (
                      <>
                        {blk.status === "Critical" && <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#ef4444" }} />}
                        {blk.status === "Warning" && <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f59e0b" }} />}
                      </>
                    )}
                  </button>
                );
              })
            ) : (
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)", fontStyle: "italic" }}>
                {["air_quality", "climate"].includes(moduleId)
                  ? "(Organisation-level telemetry scope)"
                  : "Overall facility scope active."}
              </span>
            )}
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : selectedBlockId === null ? (
        /* ========================================================================= */
        /* OVERALL FACILITY VIEW                                                     */
        /* ========================================================================= */
        <div>
          {/* Overall KPI Cards Row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "28px" }}>
            <div className="card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Current Overall</span>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--clr-primary)", marginTop: "4px" }}>
                {overallData?.current_value} {overallData?.unit}
              </div>
              <span style={{ fontSize: "11px", color: "#10b981", fontWeight: 700 }}>{overallData?.change_pct_str} vs prior window</span>
            </div>

            <div className="card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Facility Average</span>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--clr-text-primary)", marginTop: "4px" }}>
                {overallData?.average} {overallData?.unit}
              </div>
              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>Period aggregate average</span>
            </div>

            <div className="card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Peak Telemetry</span>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "#f59e0b", marginTop: "4px" }}>
                {overallData?.peak} {overallData?.unit}
              </div>
              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>Maximum recorded reading</span>
            </div>

            <div className="card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Facility Status</span>
              <div style={{ marginTop: "8px" }}>
                {getStatusBadge(overallData?.status || "Normal")}
              </div>
              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "block", marginTop: "4px" }}>
                {overallData?.open_anomalies_count || 0} active anomalies
              </span>
            </div>
          </div>

          {/* Overall Graph Card */}
          <div className="card" style={{ padding: "24px", marginBottom: "28px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <TrendingUp size={18} color="var(--clr-primary)" />
              OVERALL FACILITY TREND GRAPH ({overallData?.unit})
            </h3>

            <TimeSeriesWaveform
              data={overallData?.trend_points || []}
              moduleName={moduleId}
              unit={overallData?.unit || ""}
              locationName={`Overall Facility (${overallData?.organisation_name || activeOrgId})`}
              baseline={overallData?.baseline}
              warningThreshold={overallData?.warning_threshold}
              criticalThreshold={overallData?.critical_threshold}
              isCumulative={["energy", "water", "street_lighting"].includes(moduleId.toLowerCase().trim())}
              period={period}
              height={300}
              emptyTitle="No telemetry points recorded for overall facility."
              emptyDescription="Sensor readings will populate as data is generated or Demo Mode cycles run."
              currentValue={overallData?.current_value}
              activeAnomalyCount={overallData?.open_anomalies_count || 0}
            />
          </div>

          {/* Block-Wise Comparison Grid */}
          <div className="card" style={{ padding: "24px", marginBottom: "28px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <BarChart3 size={18} color="var(--clr-primary)" />
              BLOCK-WISE COMPARISON
            </h3>

            {overallData?.block_comparison && overallData.block_comparison.length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
                {overallData.block_comparison.map((blk) => (
                  <div
                    key={blk.block_id}
                    onClick={() => setSelectedBlockId(blk.block_id)}
                    style={{
                      padding: "16px",
                      borderRadius: "10px",
                      background: "var(--clr-surface-2)",
                      border: "1px solid var(--clr-border)",
                      cursor: "pointer",
                      transition: "transform 0.15s ease, border-color 0.15s ease",
                    }}
                    className="card-hover-effect"
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--clr-text-primary)" }}>{blk.block_name}</span>
                      {getStatusBadge(blk.status)}
                    </div>
                    <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-primary)" }}>
                      {blk.current_value} {blk.unit}
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "4px", display: "block" }}>
                      Click to inspect detailed block intelligence →
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--clr-text-muted)" }}>
                No facility blocks configured for this organisation.
              </div>
            )}
          </div>

          {/* Dynamic Prediction Table */}
          <div className="card" style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
              <TrendingUp size={18} color="var(--clr-primary)" />
              PREDICTION TABLE ({overallData?.module_title})
            </h3>
            <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginBottom: "16px" }}>
              Forecasting model predictions across Overall facility and every configured block.
            </p>

            {!overallData?.has_sufficient_history ? (
              <div style={{ padding: "30px", textAlign: "center", background: "var(--clr-surface-2)", borderRadius: "10px", color: "var(--clr-text-muted)", fontSize: "14px" }}>
                <AlertTriangle size={24} color="#f59e0b" style={{ margin: "0 auto 8px auto", display: "block" }} />
                Insufficient historical data for prediction. Keep Demo Mode ON or connect IoT sensors to accumulate historical points.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid var(--clr-border)", textAlign: "left" }}>
                      <th style={{ padding: "12px", color: "var(--clr-text-muted)" }}>Location</th>
                      <th style={{ padding: "12px", color: "var(--clr-text-muted)" }}>Current ({overallData?.unit})</th>
                      <th style={{ padding: "12px", color: "var(--clr-text-muted)" }}>Predicted ({overallData?.unit})</th>
                      <th style={{ padding: "12px", color: "var(--clr-text-muted)" }}>Projected Change</th>
                      <th style={{ padding: "12px", color: "var(--clr-text-muted)" }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overallData?.prediction_table.map((row, i) => (
                      <tr
                        key={i}
                        style={{
                          borderBottom: "1px solid var(--clr-border)",
                          background: row.location === "Overall" ? "var(--clr-primary-light)" : "transparent",
                          fontWeight: row.location === "Overall" ? 800 : 500,
                        }}
                      >
                        <td style={{ padding: "12px", color: "var(--clr-text-primary)" }}>{row.location}</td>
                        <td style={{ padding: "12px" }}>{row.current_value}</td>
                        <td style={{ padding: "12px", color: "var(--clr-primary)", fontWeight: 700 }}>{row.predicted_value}</td>
                        <td style={{ padding: "12px", color: row.change_pct_str.startsWith("+") ? "#f59e0b" : "#10b981" }}>{row.change_pct_str}</td>
                        <td style={{ padding: "12px" }}>{getStatusBadge(row.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ========================================================================= */
        /* DETAILED BLOCK VIEW                                                       */
        /* ========================================================================= */
        <div>
          {/* Back to Overall Button */}
          <div style={{ marginBottom: "20px" }}>
            <button
              onClick={() => setSelectedBlockId(null)}
              className="btn btn-outline btn-md"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontWeight: 700 }}
            >
              <ArrowLeft size={16} /> ← Back to Overall Facility View
            </button>
          </div>

          {/* Block Specific KPIs */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "28px" }}>
            <div className="card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Block Current Value</span>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--clr-primary)", marginTop: "4px" }}>
                {blockData?.current_value} {blockData?.unit}
              </div>
              <span style={{ fontSize: "11px", color: "#10b981", fontWeight: 700 }}>{blockData?.change_pct_str} trend</span>
            </div>

            <div className="card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Block Average</span>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "var(--clr-text-primary)", marginTop: "4px" }}>
                {blockData?.average} {blockData?.unit}
              </div>
              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>Block period average</span>
            </div>

            <div className="card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Block Peak</span>
              <div style={{ fontSize: "24px", fontWeight: 800, color: "#f59e0b", marginTop: "4px" }}>
                {blockData?.peak} {blockData?.unit}
              </div>
              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>Block max reading</span>
            </div>

            <div className="card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Block Status</span>
              <div style={{ marginTop: "8px" }}>
                {getStatusBadge(blockData?.status || "Normal")}
              </div>
            </div>
          </div>

          {/* Selected Block Graph */}
          <div className="card" style={{ padding: "24px", marginBottom: "28px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <TrendingUp size={18} color="var(--clr-primary)" />
              {blockData?.block_name.toUpperCase()} TREND GRAPH ({blockData?.unit})
            </h3>

            <TimeSeriesWaveform
              data={blockData?.trend_points || []}
              moduleName={moduleId}
              unit={blockData?.unit || ""}
              locationName={blockData?.block_name || "Facility Block"}
              baseline={blockData?.baseline}
              warningThreshold={blockData?.warning_threshold}
              criticalThreshold={blockData?.critical_threshold}
              isCumulative={["energy", "water", "street_lighting"].includes(moduleId.toLowerCase().trim())}
              period={period}
              height={300}
              emptyTitle={`No telemetry recorded for ${blockData?.block_name}.`}
              emptyDescription="Readings will appear as sensor data arrives for this block."
              currentValue={blockData?.current_value}
              activeAnomalyCount={(blockData?.anomalies || []).filter((a) => a.status === "OPEN" || a.status === "ACKNOWLEDGED").length}
            />
          </div>

          {/* Selected Block Prediction & Intelligence Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
            {/* Anomaly History */}
            {(() => {
              const allAnoms = blockData?.anomalies || [];
              const activeAnoms = allAnoms.filter((a) => a.status === "OPEN" || a.status === "ACKNOWLEDGED");
              const pastAnoms = allAnoms.filter((a) => a.status === "RESOLVED" || a.status === "DISMISSED");

              return (
                <div className="card" style={{ padding: "24px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                      <AlertTriangle size={18} color={activeAnoms.length > 0 ? "#ef4444" : "#10b981"} />
                      {blockData?.block_name} Anomaly History
                    </h3>
                    <Badge variant={activeAnoms.length > 0 ? "error" : "success"}>
                      {activeAnoms.length} Active
                    </Badge>
                  </div>

                  {activeAnoms.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                      {activeAnoms.map((anom) => (
                        <div
                          key={anom.id}
                          style={{
                            padding: "14px",
                            borderRadius: "8px",
                            background: "var(--clr-surface-2)",
                            border: `1px solid ${anom.severity === "CRITICAL" ? "rgba(239, 68, 68, 0.5)" : "rgba(245, 158, 11, 0.4)"}`,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                            <strong style={{ fontSize: "13px", color: "var(--clr-text-primary)" }}>{anom.metric?.toUpperCase()} Anomaly</strong>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <Badge variant={anom.severity === "CRITICAL" ? "error" : "warning"}>{anom.severity}</Badge>
                              <button
                                onClick={() => handleBlockAnomalyAction(anom.id, "RESOLVED")}
                                disabled={actionLoading[anom.id]}
                                style={{
                                  padding: "3px 8px",
                                  fontSize: "11px",
                                  borderRadius: "4px",
                                  border: "1px solid #10b981",
                                  background: "rgba(16, 185, 129, 0.15)",
                                  color: "#10b981",
                                  cursor: "pointer",
                                  fontWeight: 600,
                                }}
                              >
                                {actionLoading[anom.id] ? "..." : "Resolve"}
                              </button>
                              <button
                                onClick={() => handleBlockAnomalyAction(anom.id, "DISMISSED")}
                                disabled={actionLoading[anom.id]}
                                style={{
                                  padding: "3px 8px",
                                  fontSize: "11px",
                                  borderRadius: "4px",
                                  border: "1px solid var(--clr-border)",
                                  background: "transparent",
                                  color: "var(--clr-text-muted)",
                                  cursor: "pointer",
                                }}
                              >
                                Dismiss
                              </button>
                            </div>
                          </div>
                          <p style={{ fontSize: "12px", color: "var(--clr-text-secondary)", margin: "4px 0" }}>{anom.reason}</p>
                          <span style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>
                            {anom.timestamp ? new Date(anom.timestamp).toLocaleString() : ""} | Status: <span style={{ color: "#ef4444", fontWeight: 600 }}>{anom.status}</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ padding: "20px 16px", borderRadius: "8px", background: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", color: "#10b981", fontSize: "13px", display: "flex", alignItems: "center", gap: "10px", marginBottom: pastAnoms.length > 0 ? "16px" : "0" }}>
                      <CheckCircle2 size={20} color="#10b981" />
                      <div>
                        <strong>No active anomalies for {blockData?.block_name}.</strong>
                        <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "2px" }}>
                          Facility operating normally within configured baseline.
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Past Historical Anomalies */}
                  {pastAnoms.length > 0 && (
                    <div style={{ marginTop: "16px", borderTop: "1px solid var(--clr-border)", paddingTop: "14px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--clr-text-muted)", display: "block", marginBottom: "10px" }}>
                        Past Resolved / Dismissed Anomalies ({pastAnoms.length})
                      </span>
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {pastAnoms.slice(0, 5).map((anom) => (
                          <div
                            key={anom.id}
                            style={{
                              padding: "10px 12px",
                              borderRadius: "6px",
                              background: "var(--clr-surface-2)",
                              border: "1px solid var(--clr-border)",
                              opacity: 0.85,
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" }}>
                              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--clr-text-secondary)" }}>{anom.metric?.toUpperCase()} Anomaly</span>
                              <Badge variant={anom.status === "RESOLVED" ? "success" : "neutral"}>{anom.status}</Badge>
                            </div>
                            <p style={{ fontSize: "11px", color: "var(--clr-text-muted)", margin: "2px 0" }}>{anom.reason}</p>
                            <span style={{ fontSize: "10px", color: "var(--clr-text-muted)" }}>
                              {anom.timestamp ? new Date(anom.timestamp).toLocaleString() : ""}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {allAnoms.length === 0 && (
                    <div style={{ padding: "20px", textAlign: "center", color: "var(--clr-text-muted)", fontSize: "13px" }}>
                      <CheckCircle2 size={24} color="#10b981" style={{ margin: "0 auto 8px auto", display: "block" }} />
                      No active or past anomalies logged for {blockData?.block_name}.
                    </div>
                  )}
                </div>
              );
            })()}

            {/* AI Recommendations */}
            {(() => {
              const allRecs = blockData?.recommendations || [];
              const activeRecs = allRecs.filter((r) => r.status === "ACTIVE" || r.status === "OPEN");
              const pastRecs = allRecs.filter((r) => r.status !== "ACTIVE" && r.status !== "OPEN");

              return (
                <div className="card" style={{ padding: "24px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                    <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                      <Lightbulb size={18} color="#60a5fa" />
                      {blockData?.block_name} Recommendations
                    </h3>
                    <Badge variant={activeRecs.length > 0 ? "info" : "neutral"}>
                      {activeRecs.length} Active
                    </Badge>
                  </div>

                  {activeRecs.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                      {activeRecs.map((rec) => (
                        <div
                          key={rec.id}
                          style={{
                            padding: "14px",
                            borderRadius: "8px",
                            background: "var(--clr-surface-2)",
                            border: "1px solid var(--clr-border)",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                            <strong style={{ fontSize: "13px", color: "var(--clr-primary)" }}>{rec.summary}</strong>
                            <Badge variant="info">{rec.priority}</Badge>
                          </div>
                          {rec.recommended_actions && rec.recommended_actions.length > 0 && (
                            <ul style={{ margin: "6px 0 0 16px", padding: 0, fontSize: "12px", color: "var(--clr-text-secondary)" }}>
                              {rec.recommended_actions.map((act: string, i: number) => (
                                <li key={i}>{act}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ padding: "24px", textAlign: "center", color: "var(--clr-text-muted)", fontSize: "13px", background: "rgba(59, 130, 246, 0.05)", borderRadius: "8px", border: "1px solid rgba(59, 130, 246, 0.15)" }}>
                      <CheckCircle2 size={24} color="#10b981" style={{ margin: "0 auto 8px auto", display: "block" }} />
                      No active recommendations for {blockData?.block_name}.
                    </div>
                  )}

                  {/* Past / Actioned Recommendations History */}
                  {pastRecs.length > 0 && (
                    <div style={{ marginTop: "16px", borderTop: "1px solid var(--clr-border)", paddingTop: "14px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--clr-text-muted)", display: "block", marginBottom: "10px" }}>
                        Actioned / Past Recommendations ({pastRecs.length})
                      </span>
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {pastRecs.slice(0, 5).map((rec) => (
                          <div
                            key={rec.id}
                            style={{
                              padding: "10px 12px",
                              borderRadius: "6px",
                              background: "var(--clr-surface-2)",
                              border: "1px solid var(--clr-border)",
                              opacity: 0.8,
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" }}>
                              <span style={{ fontSize: "12px", color: "var(--clr-text-secondary)" }}>{rec.summary}</span>
                              <Badge variant={rec.status === "RESOLVED" || rec.status === "ACTIONED" ? "success" : "neutral"}>
                                {rec.status}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        </div>
      )}
    </AppLayout>
  );
}

export default function ModuleDetailPage() {
  return (
    <Suspense
      fallback={
        <AppLayout>
          <div style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
            Loading module intelligence...
          </div>
        </AppLayout>
      }
    >
      <ModuleDetailContent />
    </Suspense>
  );
}
