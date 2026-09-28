"use client";

import React, { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { api, API_BASE_URL } from "@/lib/api";
import { IoTDevice } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Cpu, RefreshCw, Wifi, Code2, BookOpen, CheckCircle, ShieldCheck } from "lucide-react";

export default function IoTPage() {
  const { activeOrgId } = useAuth();
  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [guideModalOpen, setGuideModalOpen] = useState<boolean>(false);

  const loadDevices = async () => {
    if (!activeOrgId) return;
    setLoading(true);
    try {
      const res = await api.get<IoTDevice[]>(`/api/v1/iot/devices`, { organisation_id: activeOrgId });
      setDevices(res);
    } catch {
      // Fallback demo hardware if no endpoint
      setDevices([
        {
          id: "DEV-ESP32-01",
          organisation_id: activeOrgId,
          device_name: "ESP32 Energy Monitor (Zone A)",
          mac_address: "A4:CF:12:89:56:01",
          location: "Main Substation",
          status: "online",
          last_seen: new Date().toISOString(),
          firmware_version: "v2.1.4-green",
        },
        {
          id: "DEV-ESP32-02",
          organisation_id: activeOrgId,
          device_name: "Wokwi Flow Sensor (Zone B)",
          mac_address: "A4:CF:12:89:56:02",
          location: "Water Treatment Room",
          status: "online",
          last_seen: new Date().toISOString(),
          firmware_version: "v2.1.4-green",
        },
        {
          id: "DEV-ESP32-03",
          organisation_id: activeOrgId,
          device_name: "Wokwi Climate Node (Zone C)",
          mac_address: "A4:CF:12:89:56:03",
          location: "Server Room 102",
          status: "offline",
          last_seen: new Date(Date.now() - 86400000).toISOString(),
          firmware_version: "v2.0.1-green",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDevices();
  }, [activeOrgId]);

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px", margin: 0 }}>
            <Cpu color="var(--clr-primary)" /> IoT Device Management
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", margin: "4px 0 0 0" }}>
            ESP32/Wokwi devices send sensor readings to GreenNexa through the authenticated IoT API.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            onClick={() => setGuideModalOpen(true)}
            className="btn btn-outline btn-sm"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <BookOpen size={14} />
            <span>Wokwi IoT Demo Guide</span>
          </button>

          <button onClick={loadDevices} className="btn btn-primary btn-sm" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Security & Authentication Notice */}
      <div
        style={{
          padding: "14px 18px",
          borderRadius: "10px",
          backgroundColor: "rgba(56, 189, 248, 0.1)",
          border: "1px solid rgba(56, 189, 248, 0.25)",
          color: "#38bdf8",
          fontSize: "0.85rem",
          marginBottom: "24px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <ShieldCheck size={18} />
        <span>
          <strong>Device Authentication:</strong> Hardware devices authenticate using <code>X-Device-ID</code> and <code>X-API-Key</code> headers over HTTPS. Device secrets are kept strictly isolated per organisation.
        </span>
      </div>

      {/* Hardware Table */}
      <div className="card" style={{ padding: "0", overflow: "hidden", marginBottom: "32px" }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--clr-border-light)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>Registered Sensors & Gateways</h2>
          <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Total: {devices.length} Devices</span>
        </div>

        {loading ? (
          <div style={{ padding: "24px" }}>
            <Skeleton height="40px" style={{ marginBottom: "12px" }} />
            <Skeleton height="40px" />
          </div>
        ) : devices.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "14px" }}>
              <thead>
                <tr style={{ background: "var(--clr-surface-2)", borderBottom: "1px solid var(--clr-border)", color: "var(--clr-text-secondary)" }}>
                  <th style={{ padding: "12px 20px" }}>Device Name</th>
                  <th style={{ padding: "12px 20px" }}>Device ID</th>
                  <th style={{ padding: "12px 20px" }}>MAC Address</th>
                  <th style={{ padding: "12px 20px" }}>Location</th>
                  <th style={{ padding: "12px 20px" }}>Status</th>
                  <th style={{ padding: "12px 20px" }}>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((dev) => (
                  <tr key={dev.id} style={{ borderBottom: "1px solid var(--clr-border-light)" }}>
                    <td style={{ padding: "14px 20px", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
                      <Wifi size={16} color="var(--clr-primary)" />
                      {dev.device_name}
                    </td>
                    <td style={{ padding: "14px 20px", fontFamily: "monospace", fontSize: "13px" }}>{dev.id}</td>
                    <td style={{ padding: "14px 20px", fontFamily: "monospace", fontSize: "13px" }}>{dev.mac_address}</td>
                    <td style={{ padding: "14px 20px" }}>{dev.location || "N/A"}</td>
                    <td style={{ padding: "14px 20px" }}>
                      <Badge variant={dev.status === "online" ? "success" : "neutral"}>
                        {dev.status.toUpperCase()}
                      </Badge>
                    </td>
                    <td style={{ padding: "14px 20px", color: "var(--clr-text-muted)", fontSize: "13px" }}>
                      {dev.last_seen ? new Date(dev.last_seen).toLocaleString() : "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No IoT devices registered" description="No physical microcontrollers have been provisioned for this organisation yet." />
        )}
      </div>

      {/* ESP32 HTTP Payload Documentation Box */}
      <div className="card" style={{ background: "var(--clr-surface-2)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
          <Code2 size={20} color="var(--clr-primary)" />
          <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>Authenticated Ingestion Payload</h3>
        </div>
        <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginBottom: "16px" }}>
          Endpoint: <code>POST /api/v1/iot/sensor-data</code> | Headers: <code>X-Device-ID: DEVICE_ID</code>, <code>X-API-Key: API_KEY</code>
        </p>
        <pre
          style={{
            background: "#0f172a",
            color: "#f8fafc",
            padding: "16px",
            borderRadius: "8px",
            fontSize: "13px",
            fontFamily: "monospace",
            overflowX: "auto",
          }}
        >
{`{
  "device_id": "DEV-CAMPUS-01",
  "readings": [
    { "sensor_type": "energy", "value": 1150.5, "unit": "kWh" },
    { "sensor_type": "water", "value": 340.0, "unit": "L" },
    { "sensor_type": "temperature", "value": 24.5, "unit": "°C" }
  ]
}`}
        </pre>
      </div>

      {/* Wokwi IoT Demo Guide Modal */}
      {guideModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.8)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            style={{
              backgroundColor: "#1e293b",
              borderRadius: "12px",
              padding: "28px",
              maxWidth: "680px",
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              color: "#f8fafc",
              border: "1px solid rgba(16, 185, 129, 0.3)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <BookOpen color="#10b981" /> Wokwi / ESP32 IoT Demo Guide
              </h2>
              <button
                onClick={() => setGuideModalOpen(false)}
                style={{ background: "transparent", border: "none", color: "#94a3b8", fontSize: "1.25rem", cursor: "pointer" }}
              >
                &times;
              </button>
            </div>

            <p style={{ fontSize: "0.9rem", color: "#cbd5e1", lineHeight: 1.6 }}>
              You can connect Wokwi simulated ESP32 boards or physical microcontrollers to GreenNexa in 3 simple steps:
            </p>

            <ol style={{ fontSize: "0.85rem", color: "#cbd5e1", lineHeight: 1.7, paddingLeft: "20px", marginBottom: "20px" }}>
              <li>Configure Wi-Fi connection (for Wokwi use SSID <code>Wokwi-GUEST</code>).</li>
              <li>Set target endpoint to <code>{API_BASE_URL}/api/v1/iot/sensor-data</code>.</li>
              <li>Add HTTP headers <code>X-Device-ID: DEVICE_ID</code> and <code>X-API-Key: API_KEY</code>.</li>
            </ol>

            <h3 style={{ fontSize: "1rem", color: "#38bdf8", marginBottom: "8px" }}>C++ / Arduino Snippet</h3>
            <pre style={{ background: "#0f172a", color: "#f8fafc", padding: "12px", borderRadius: "6px", fontSize: "0.8rem", overflowX: "auto" }}>
{`HTTPClient http;
http.begin("${API_BASE_URL}/api/v1/iot/sensor-data");
http.addHeader("Content-Type", "application/json");
http.addHeader("X-Device-ID", "DEVICE_ID");
http.addHeader("X-API-Key", "API_KEY");

String payload = "{\\"device_id\\":\\"DEVICE_ID\\",\\"readings\\":[{\\"sensor_type\\":\\"energy\\",\\"value\\":1250.0,\\"unit\\":\\"kWh\\"}]}";
int code = http.POST(payload);`}
            </pre>

            <div style={{ marginTop: "20px", textAlign: "right" }}>
              <button
                onClick={() => setGuideModalOpen(false)}
                style={{ backgroundColor: "#10b981", color: "#fff", border: "none", padding: "8px 16px", borderRadius: "6px", cursor: "pointer" }}
              >
                Close Guide
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}

