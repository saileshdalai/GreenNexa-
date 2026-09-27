"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useDemo } from "@/context/DemoContext";

import { api } from "@/lib/api";

interface SimulatorStatus {
  running: boolean;
  interval_seconds: number;
  organisations_processed: number;
  last_run_at: string | null;
  next_run_at: string | null;
  total_readings_generated: number;
  total_anomalies_generated: number;
  demo_mode?: boolean;
}

interface DemoControlPanelProps {
  onRefreshDashboard?: () => void;
}

export const DemoControlPanel: React.FC<DemoControlPanelProps> = ({ onRefreshDashboard }) => {
  const { token, user } = useAuth();
  const { startWalkthrough } = useDemo();
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const fetchStatus = async () => {
    if (!token) return;
    try {
      const effectiveOrg = user?.organisation_id || getOrgId();
      const data = await api.get<SimulatorStatus>(
        "/api/v1/simulator/synthetic/status",
        effectiveOrg ? { organisation_id: effectiveOrg } : undefined
      );
      setStatus(data);
    } catch {
      // Ignore errors silently for viewer role or offline state
    }
  };

  useEffect(() => {
    fetchStatus();
    const timer = setInterval(fetchStatus, 15000);
    return () => clearInterval(timer);
  }, [token]);

  const getOrgId = (): string | undefined => {
    if (user?.organisation_id) return user.organisation_id;
    if (typeof window !== "undefined") {
      const org =
        localStorage.getItem("greennexa_active_org") ||
        localStorage.getItem("greennexa_active_org_id");
      if (org && org !== "null" && org !== "undefined" && org.trim() !== "") return org.trim();
    }
    return undefined;
  };

  const handleStart = async () => {
    if (!token) return;
    setLoading(true);
    setMessage(null);
    try {
      const orgId = getOrgId();
      const data = await api.post<SimulatorStatus>("/api/v1/simulator/synthetic/start", {
        interval_seconds: 30,
        demo_mode: true,
        ...(orgId ? { organisation_id: orgId } : {}),
      });
      setStatus(data);
      setMessage({ text: "Simulator started successfully (30-second cycle).", type: "success" });
      if (onRefreshDashboard) onRefreshDashboard();
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to start simulator.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (!token) return;
    setLoading(true);
    setMessage(null);
    try {
      const orgId = getOrgId();
      const data = await api.post<SimulatorStatus>(
        "/api/v1/simulator/synthetic/stop",
        orgId ? { organisation_id: orgId } : {}
      );
      setStatus(data);
      setMessage({ text: "Simulator stopped.", type: "success" });
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to stop simulator.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReading = async () => {
    if (!token) return;
    setLoading(true);
    setMessage(null);
    try {
      const data = await api.post<any>("/api/v1/simulator/synthetic/generate-reading");
      setMessage({
        text: `Generated ${data.readings_generated} fresh sensor readings!`,
        type: "success",
      });
      if (onRefreshDashboard) onRefreshDashboard();
      fetchStatus();
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to generate reading.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAnomaly = async () => {
    if (!token) return;
    setLoading(true);
    setMessage(null);
    try {
      const data = await api.post<any>("/api/v1/simulator/synthetic/generate-anomaly?sensor_type=energy");
      setMessage({
        text: `Triggered high-severity Energy Anomaly (${data.details?.[0]?.value || 1850} kWh)! Processing AI Recommendation & Alert...`,
        type: "success",
      });
      if (onRefreshDashboard) onRefreshDashboard();
      fetchStatus();
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to trigger anomaly.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleResetData = async () => {
    if (!token) return;
    if (!confirm("Reset synthetic demo data for this facility? This will clear synthetic readings & anomalies.")) {
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const data = await api.post<any>("/api/v1/simulator/synthetic/reset-demo");
      setMessage({
        text: `Demo reset complete: cleared ${data.readings_deleted} readings and ${data.anomalies_deleted} anomalies.`,
        type: "success",
      });
      if (onRefreshDashboard) onRefreshDashboard();
      fetchStatus();
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to reset demo data.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const canControl = user?.role === "SUPER_ADMIN" || user?.role === "ADMIN";

  return (
    <div
      style={{
        backgroundColor: "var(--color-bg-card, #1e293b)",
        borderRadius: "12px",
        padding: "20px",
        border: "1px solid rgba(255,255,255,0.08)",
        marginBottom: "24px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 600, color: "var(--color-text-main, #f8fafc)", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>Demo Control Panel</span>
            <span
              style={{
                fontSize: "0.75rem",
                padding: "2px 8px",
                borderRadius: "12px",
                backgroundColor: status?.running ? "rgba(16, 185, 129, 0.2)" : "rgba(148, 163, 184, 0.2)",
                color: status?.running ? "#10b981" : "#94a3b8",
                fontWeight: 500,
              }}
            >
              Simulator: {status?.running ? "RUNNING" : "STOPPED"}
              {status?.demo_mode ? " · DEMO ON" : ""}
            </span>
          </h3>
          <p style={{ margin: "4px 0 0 0", fontSize: "0.85rem", color: "var(--color-text-muted, #94a3b8)" }}>
            Data Source: <strong style={{ color: "#38bdf8" }}>Synthetic</strong> | Interval: 30s
            {status?.last_run_at && ` | Last generated: ${new Date(status.last_run_at).toLocaleTimeString()}`}
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={startWalkthrough}
            style={{
              backgroundColor: "#6366f1",
              color: "#ffffff",
              border: "none",
              padding: "8px 14px",
              borderRadius: "6px",
              fontSize: "0.85rem",
              fontWeight: 500,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>Guide Walkthrough</span>
          </button>
        </div>
      </div>

      {message && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: "6px",
            fontSize: "0.85rem",
            marginBottom: "16px",
            backgroundColor: message.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
            color: message.type === "success" ? "#34d399" : "#fca5a5",
            border: `1px solid ${message.type === "success" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
          }}
        >
          {message.text}
        </div>
      )}

      {canControl ? (
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          {status?.running ? (
            <button
              onClick={handleStop}
              disabled={loading}
              style={{
                backgroundColor: "rgba(239, 68, 68, 0.2)",
                color: "#f87171",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                padding: "8px 14px",
                borderRadius: "6px",
                fontSize: "0.85rem",
                fontWeight: 500,
                cursor: loading ? "wait" : "pointer",
              }}
            >
              Stop Simulator
            </button>
          ) : (
            <button
              onClick={handleStart}
              disabled={loading}
              style={{
                backgroundColor: "rgba(16, 185, 129, 0.2)",
                color: "#34d399",
                border: "1px solid rgba(16, 185, 129, 0.4)",
                padding: "8px 14px",
                borderRadius: "6px",
                fontSize: "0.85rem",
                fontWeight: 500,
                cursor: loading ? "wait" : "pointer",
              }}
            >
              Start Simulator
            </button>
          )}

          <button
            onClick={handleGenerateReading}
            disabled={loading}
            style={{
              backgroundColor: "rgba(56, 189, 248, 0.15)",
              color: "#38bdf8",
              border: "1px solid rgba(56, 189, 248, 0.3)",
              padding: "8px 14px",
              borderRadius: "6px",
              fontSize: "0.85rem",
              fontWeight: 500,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            Generate Reading
          </button>

          <button
            onClick={handleGenerateAnomaly}
            disabled={loading}
            style={{
              backgroundColor: "rgba(245, 158, 11, 0.15)",
              color: "#fbbf24",
              border: "1px solid rgba(245, 158, 11, 0.3)",
              padding: "8px 14px",
              borderRadius: "6px",
              fontSize: "0.85rem",
              fontWeight: 500,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            Generate Demo Anomaly
          </button>

          <button
            onClick={handleResetData}
            disabled={loading}
            style={{
              backgroundColor: "rgba(148, 163, 184, 0.15)",
              color: "#cbd5e1",
              border: "1px solid rgba(148, 163, 184, 0.3)",
              padding: "8px 14px",
              borderRadius: "6px",
              fontSize: "0.85rem",
              fontWeight: 500,
              cursor: loading ? "wait" : "pointer",
            }}
          >
            Reset Demo Data
          </button>
        </div>
      ) : (
        <p style={{ margin: 0, fontSize: "0.85rem", color: "#94a3b8", fontStyle: "italic" }}>
          Viewing as {user?.role}. Simulator controls are restricted to facility Administrators.
        </p>
      )}
    </div>
  );
};
