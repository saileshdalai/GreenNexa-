"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { PlatformAlertItem } from "@/types";
import {
  Bell,
  AlertTriangle,
  RefreshCw,
  Search,
  Building,
  Clock,
  ShieldAlert,
} from "lucide-react";

export default function PlatformAlertsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [alerts, setAlerts] = useState<PlatformAlertItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const data = await api.get<PlatformAlertItem[]>("/api/v1/super-admin/alerts");
      setAlerts(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load platform alerts", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadAlerts();
  }, [user]);

  const filtered = alerts.filter(
    (a) =>
      a.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (a.organisation_name && a.organisation_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <AppLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
            <Bell color="var(--clr-primary)" size={28} />
            Platform & System Alerts
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            System-level notifications, offline IoT device alerts, and setup warnings.
          </p>
        </div>

        <button onClick={loadAlerts} className="btn btn-outline btn-sm" title="Refresh">
          <RefreshCw size={14} className={loading ? "spin" : ""} />
        </button>
      </div>

      {/* Filter */}
      <div className="card" style={{ padding: "20px", marginBottom: "24px" }}>
        <div style={{ position: "relative" }}>
          <Search size={16} color="var(--clr-text-muted)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            className="form-input"
            placeholder="Search platform alerts..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ paddingLeft: "36px" }}
          />
        </div>
      </div>

      {/* Alerts List */}
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        {filtered.length === 0 ? (
          <div className="card" style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
            {loading ? "Loading alerts..." : "No active platform alerts recorded."}
          </div>
        ) : (
          filtered.map((alert) => (
            <div
              key={alert.id}
              className="card"
              style={{
                padding: "20px",
                borderLeft: `4px solid ${
                  alert.severity === "CRITICAL" ? "#ef4444" : alert.severity === "HIGH" ? "#f59e0b" : "#3b82f6"
                }`,
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <ShieldAlert size={18} color={alert.severity === "CRITICAL" ? "#ef4444" : "#f59e0b"} />
                  <h3 style={{ fontSize: "16px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
                    {alert.title}
                  </h3>
                </div>

                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 800,
                    padding: "3px 8px",
                    borderRadius: "6px",
                    background: alert.severity === "CRITICAL" ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)",
                    color: alert.severity === "CRITICAL" ? "#ef4444" : "#d97706",
                  }}
                >
                  {alert.severity}
                </span>
              </div>

              <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: 0 }}>
                {alert.description}
              </p>

              <div style={{ display: "flex", gap: "16px", fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
                {alert.organisation_name && (
                  <span>🏢 {alert.organisation_name}</span>
                )}
                <span><Clock size={12} style={{ display: "inline", marginRight: "4px" }} /> {new Date(alert.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </AppLayout>
  );
}
