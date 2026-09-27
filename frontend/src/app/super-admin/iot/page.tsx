"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { IoTDevice } from "@/types";
import {
  Cpu,
  RefreshCw,
  Search,
  Wifi,
  WifiOff,
  Power,
  Clock,
  Building,
} from "lucide-react";

export default function PlatformIoTDevicesPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");

  const loadDevices = async () => {
    setLoading(true);
    try {
      const data = await api.get<IoTDevice[]>("/api/v1/super-admin/iot");
      setDevices(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load IoT devices", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadDevices();
  }, [user]);

  const filtered = devices.filter(
    (d) =>
      (d.device_name && d.device_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (d.device_id && d.device_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (d.organisation_name && d.organisation_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (d.device_type && d.device_type.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <AppLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
            <Cpu color="var(--clr-primary)" size={28} />
            Platform IoT Devices
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            Platform-wide hardware and simulator IoT device registry. API keys are kept encrypted.
          </p>
        </div>

        <button onClick={loadDevices} className="btn btn-outline btn-sm" title="Refresh">
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
            placeholder="Search devices by Device ID, Name, Organisation, or Type..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ paddingLeft: "36px" }}
          />
        </div>
      </div>

      {/* IoT Devices Table */}
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ background: "var(--clr-surface-2)", borderBottom: "2px solid var(--clr-border)", textAlign: "left", color: "var(--clr-text-muted)", fontSize: "12px", fontWeight: 700, textTransform: "uppercase" }}>
                <th style={{ padding: "14px 20px" }}>Device ID & Name</th>
                <th style={{ padding: "14px 20px" }}>Organisation</th>
                <th style={{ padding: "14px 20px" }}>Device Type</th>
                <th style={{ padding: "14px 20px" }}>Sensor Type</th>
                <th style={{ padding: "14px 20px" }}>Status</th>
                <th style={{ padding: "14px 20px" }}>Last Telemetry Seen</th>
                <th style={{ padding: "14px 20px", textAlign: "right" }}>Source</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
                    {loading ? "Loading IoT devices..." : "No registered IoT devices found."}
                  </td>
                </tr>
              ) : (
                filtered.map((d) => (
                  <tr key={d.id} style={{ borderBottom: "1px solid var(--clr-border-light)" }} className="table-row-hover">
                    <td style={{ padding: "16px 20px" }}>
                      <div style={{ fontWeight: 800, fontSize: "14px", color: "var(--clr-text-primary)" }}>{d.device_name || d.device_id}</div>
                      <div style={{ fontSize: "11px", color: "var(--clr-primary)", fontFamily: "monospace", fontWeight: 700 }}>{d.device_id}</div>
                    </td>

                    <td style={{ padding: "16px 20px" }}>
                      <div style={{ fontWeight: 600 }}>{d.organisation_name || "Unassigned"}</div>
                      <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>{d.organisation_id}</div>
                    </td>

                    <td style={{ padding: "16px 20px" }}>
                      <span style={{ background: "var(--clr-surface-2)", border: "1px solid var(--clr-border)", padding: "3px 8px", borderRadius: "6px", fontWeight: 600 }}>
                        {d.device_type || "ESP32"}
                      </span>
                    </td>

                    <td style={{ padding: "16px 20px" }}>
                      <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 6px", borderRadius: "4px", background: "var(--clr-primary-light)", color: "var(--clr-primary)" }}>
                        {d.sensor_type || "Multi-Sensor"}
                      </span>
                    </td>

                    <td style={{ padding: "16px 20px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 700, padding: "3px 8px", borderRadius: "9999px", display: "inline-flex", alignItems: "center", gap: "6px", background: d.status === "ONLINE" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)", color: d.status === "ONLINE" ? "#10b981" : "#ef4444" }}>
                        {d.status === "ONLINE" ? <Wifi size={12} /> : <WifiOff size={12} />}
                        {d.status}
                      </span>
                    </td>

                    <td style={{ padding: "16px 20px", color: "var(--clr-text-muted)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <Clock size={13} />
                        {d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : "Never"}
                      </div>
                    </td>

                    <td style={{ padding: "16px 20px", textAlign: "right", fontWeight: 700, textTransform: "uppercase", fontSize: "11px", color: "var(--clr-text-muted)" }}>
                      {d.source || "iot"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
}
