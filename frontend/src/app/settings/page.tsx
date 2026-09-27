"use client";

import React, { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { OrganisationSensorConfig, DataSourceType } from "@/types";
import { Settings, Cpu, Activity, Save, Shield, AlertTriangle, Trash2, RefreshCw, Sun, Moon, MapPin, Plus, CheckCircle2, XCircle } from "lucide-react";
import { DataSourceBadge } from "@/components/ui/DataSourceBadge";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";

export default function SettingsPage() {
  const { user, activeOrgId } = useAuth();
  const { showToast } = useToast();
  const { isModuleUnread } = useNotifications();

  const [activeTab, setActiveTab] = useState<"general" | "wards">("general");
  const [isMunicipality, setIsMunicipality] = useState<boolean>(false);
  const [wards, setWards] = useState<Array<{ block_id: string; block_name: string; is_active: boolean }>>([]);
  const [newWardName, setNewWardName] = useState("");
  const [wardLoading, setWardLoading] = useState(false);

  const [config, setConfig] = useState<OrganisationSensorConfig | null>(null);
  const [dataSource, setDataSource] = useState<DataSourceType>("synthetic");
  const [enableEnergy, setEnableEnergy] = useState<boolean>(true);
  const [enableWater, setEnableWater] = useState<boolean>(true);
  const [enableWaste, setEnableWaste] = useState<boolean>(true);
  const [enableTemp, setEnableTemp] = useState<boolean>(true);
  const [enableHum, setEnableHum] = useState<boolean>(true);
  const [enableCo2, setEnableCo2] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);

  // Danger Zone Clear Data state
  const [showClearModal, setShowClearModal] = useState<boolean>(false);
  const [clearing, setClearing] = useState<boolean>(false);
  const [clearConfirmed, setClearConfirmed] = useState<boolean>(false);

  // Check query params for tab=wards
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("tab") === "wards") {
        setActiveTab("wards");
      }
    }
  }, []);

  // Detect municipality organisation
  useEffect(() => {
    if (!activeOrgId) return;
    api.get<any>(`/api/v1/organisations/${activeOrgId}`)
      .then((org) => {
        const isM = org?.org_type && (org.org_type as string).toLowerCase().includes("municipality");
        setIsMunicipality(Boolean(isM));
      })
      .catch(() => {});
  }, [activeOrgId]);

  const loadConfig = async () => {
    if (!activeOrgId) return;
    try {
      const res = await api.get<OrganisationSensorConfig>(`/api/v1/organisations/${activeOrgId}/sensor-config`);
      setConfig(res);
      setDataSource(res.data_source);
      setEnableEnergy(res.enable_energy ?? true);
      setEnableWater(res.enable_water ?? true);
      setEnableWaste(res.enable_waste ?? true);
      setEnableTemp(res.enable_temperature ?? true);
      setEnableHum(res.enable_humidity ?? true);
      setEnableCo2(res.enable_co2 ?? true);
    } catch {
      // Create defaults
      setDataSource("synthetic");
    }
  };

  const loadWards = async () => {
    if (!activeOrgId) return;
    setWardLoading(true);
    try {
      const res = await api.get<any>(`/api/v1/organisations/${activeOrgId}/blocks`);
      setWards(res?.items || res?.blocks || []);
    } catch (err: any) {
      showToast(err.message || "Failed to load wards.", "error");
    } finally {
      setWardLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, [activeOrgId]);

  useEffect(() => {
    if (activeTab === "wards" || isMunicipality) {
      loadWards();
    }
  }, [activeTab, activeOrgId, isMunicipality]);

  const handleAddWard = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = newWardName.trim();
    if (!name) return showToast("Ward name cannot be empty.", "error");
    if (!activeOrgId) return;
    setWardLoading(true);
    try {
      await api.post(`/api/v1/organisations/${activeOrgId}/blocks`, { block_name: name });
      setNewWardName("");
      showToast("Ward added successfully!", "success");
      await loadWards();
    } catch (err: any) {
      showToast(err.message || "Failed to add ward.", "error");
    } finally {
      setWardLoading(false);
    }
  };

  const handleDeactivateWard = async (blockId: string) => {
    if (!activeOrgId) return;
    setWardLoading(true);
    try {
      await api.delete(`/api/v1/organisations/${activeOrgId}/blocks/${blockId}`);
      showToast("Ward deactivated successfully.", "success");
      await loadWards();
    } catch (err: any) {
      showToast(err.message || "Failed to deactivate ward.", "error");
    } finally {
      setWardLoading(false);
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await api.put<OrganisationSensorConfig>(`/api/v1/organisations/${activeOrgId}/sensor-config`, {
        data_source: dataSource,
        enable_energy: enableEnergy,
        enable_water: enableWater,
        enable_waste: enableWaste,
        enable_temperature: enableTemp,
        enable_humidity: enableHum,
        enable_co2: enableCo2,
      });
      setConfig(res);
      showToast("Organisation sensor configuration updated successfully!", "success");
    } catch (err: any) {
      showToast(err.message || "Failed to update sensor configuration", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleClearData = async () => {
    if (!activeOrgId || clearing) return;
    setClearing(true);
    try {
      const res = await api.post<{ message: string; cleared_records: any }>(
        `/api/v1/organisations/${activeOrgId}/clear-data`
      );
      showToast(res.message || "Organisation telemetry, anomalies, recommendations and logs reset successfully!", "success");
      setShowClearModal(false);
      setClearConfirmed(false);
      // Reload config / page state
      await loadConfig();
    } catch (err: any) {
      showToast(err.message || "Failed to clear organisation data", "error");
    } finally {
      setClearing(false);
    }
  };

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px" }}>
            <Settings color="var(--clr-primary)" /> Organisation Settings
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)" }}>
            Configure active sensor metrics, data source mode, and data management policies
          </p>
        </div>

        <DataSourceBadge source={dataSource} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "800px" }}>
        {/* Tab Switcher if Municipality */}
        {isMunicipality && (
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              onClick={() => setActiveTab("general")}
              style={{
                padding: "8px 18px",
                borderRadius: "8px",
                fontWeight: 700,
                fontSize: "13px",
                border: "none",
                cursor: "pointer",
                background: activeTab === "general" ? "var(--clr-primary)" : "var(--clr-surface-2)",
                color: activeTab === "general" ? "#ffffff" : "var(--clr-text-secondary)",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <Settings size={15} /> General Settings
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("wards")}
              style={{
                padding: "8px 18px",
                borderRadius: "8px",
                fontWeight: 700,
                fontSize: "13px",
                border: "none",
                cursor: "pointer",
                background: activeTab === "wards" ? "#0284c7" : "var(--clr-surface-2)",
                color: activeTab === "wards" ? "#ffffff" : "var(--clr-text-secondary)",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <MapPin size={15} /> Wards Management
              {wards.length > 0 && (
                <span style={{ background: "rgba(255,255,255,0.25)", padding: "1px 6px", borderRadius: "10px", fontSize: "11px" }}>
                  {wards.length}
                </span>
              )}
            </button>
          </div>
        )}

        {activeTab === "general" && (
          <>
            {/* Appearance & Theme Card */}
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
                <div>
                  <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <Sun size={18} color="var(--clr-primary)" /> Appearance & Theme
                  </h2>
                  <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: 0 }}>
                    Toggle between professional Day Mode (☀️ light dashboard) and Night Mode (🌙 dark dashboard).
                  </p>
                </div>
                <ThemeToggle />
              </div>
            </div>

        <form onSubmit={handleSaveConfig} style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* User & Role Overview Card */}
          <div className="card">
            <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Shield size={18} color="var(--clr-primary)" /> Profile & Security Info
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", fontSize: "14px" }}>
              <div>
                <span style={{ color: "var(--clr-text-muted)" }}>Authenticated User:</span>
                <div style={{ fontWeight: 600 }}>{user?.email}</div>
              </div>
              <div>
                <span style={{ color: "var(--clr-text-muted)" }}>Assigned Role:</span>
                <div style={{ fontWeight: 600 }}>{user?.role}</div>
              </div>
              <div>
                <span style={{ color: "var(--clr-text-muted)" }}>Active Organisation ID:</span>
                <div style={{ fontWeight: 600 }}>{activeOrgId}</div>
              </div>
            </div>
          </div>

          {/* Mutually Exclusive Data Source Selection Card */}
          <div className="card" style={{ borderLeft: "4px solid var(--clr-primary)" }}>
            <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>Active Data Source Mode</h2>
            <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginBottom: "20px" }}>
              Select exactly ONE data source. Both sources will NEVER run concurrently for the same organisation.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div
                onClick={() => setDataSource("synthetic")}
                style={{
                  padding: "20px",
                  borderRadius: "12px",
                  border: `2px solid ${dataSource === "synthetic" ? "var(--clr-primary)" : "var(--clr-border)"}`,
                  background: dataSource === "synthetic" ? "var(--clr-primary-light)" : "var(--clr-surface)",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                  <Activity size={20} color={dataSource === "synthetic" ? "var(--clr-primary-dark)" : "var(--clr-text-secondary)"} />
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: dataSource === "synthetic" ? "var(--clr-primary-dark)" : "var(--clr-text-primary)" }}>
                    Synthetic Simulator Mode
                  </h3>
                </div>
                <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", lineHeight: "1.5" }}>
                  Automated 30-second background sensor simulator generating realistic facility readings and statistical anomalies.
                </p>
              </div>

              <div
                onClick={() => setDataSource("iot")}
                style={{
                  padding: "20px",
                  borderRadius: "12px",
                  border: `2px solid ${dataSource === "iot" ? "var(--clr-primary)" : "var(--clr-border)"}`,
                  background: dataSource === "iot" ? "var(--clr-primary-light)" : "var(--clr-surface)",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                  <Cpu size={20} color={dataSource === "iot" ? "var(--clr-primary-dark)" : "var(--clr-text-secondary)"} />
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: dataSource === "iot" ? "var(--clr-primary-dark)" : "var(--clr-text-primary)" }}>
                    Real IoT Sensor Mode
                  </h3>
                </div>
                <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", lineHeight: "1.5" }}>
                  Accepts real HTTP ingestion payloads from ESP32 microcontrollers and Wokwi hardware simulators.
                </p>
              </div>
            </div>
          </div>

          {/* Enabled Sensor Metrics Toggles */}
          <div className="card">
            <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>Sensor Metric Enablement</h2>
            <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginBottom: "20px" }}>
              Enable or disable specific measurable domains for this organisation.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
              {[
                { label: "Energy Consumption", metric: "energy", state: enableEnergy, setter: setEnableEnergy },
                { label: "Water Usage", metric: "water", state: enableWater, setter: setEnableWater },
                { label: "Waste Generation", metric: "waste", state: enableWaste, setter: setEnableWaste },
                { label: "Indoor Temperature", metric: "temperature", state: enableTemp, setter: setEnableTemp },
                { label: "Relative Humidity", metric: "humidity", state: enableHum, setter: setEnableHum },
                { label: "CO₂ Concentration", metric: "co2", state: enableCo2, setter: setEnableCo2 },
              ].map((s) => {
                const hasUnread = isModuleUnread(s.metric);
                return (
                  <label
                    key={s.label}
                    data-testid={`setting-metric-${s.metric}`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "12px 16px",
                      borderRadius: "8px",
                      background: "var(--clr-surface-2)",
                      border: "1px solid var(--clr-border)",
                      cursor: "pointer",
                      fontSize: "14px",
                      fontWeight: 600,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span>{s.label}</span>
                      {hasUnread && <RedDotIndicator size="sm" label={`${s.label} — unread anomaly`} />}
                    </div>
                    <input
                      type="checkbox"
                      checked={s.state}
                      onChange={(e) => s.setter(e.target.checked)}
                      style={{ width: "18px", height: "18px", accentColor: "var(--clr-primary)", cursor: "pointer" }}
                    />
                  </label>
                );
              })}
            </div>
          </div>

          {/* Save Button */}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="submit"
              disabled={saving}
              className="btn btn-primary btn-lg"
              style={{ display: "flex", alignItems: "center", gap: "8px" }}
            >
              <Save size={18} />
              {saving ? "Saving Configuration..." : "Save Configuration"}
            </button>
          </div>
        </form>

        {/* Danger Zone Card - Admin Clear Data */}
        <div
          className="card"
          style={{
            border: "1px solid #fca5a5",
            background: "#fff5f5",
            borderRadius: "12px",
            padding: "24px",
            marginTop: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: "14px" }}>
            <div
              style={{
                padding: "10px",
                borderRadius: "10px",
                background: "#fee2e2",
                color: "#dc2626",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <AlertTriangle size={24} />
            </div>

            <div style={{ flex: 1 }}>
              <h2 style={{ fontSize: "18px", fontWeight: 800, color: "#991b1b", marginBottom: "6px" }}>
                Danger Zone: Reset Operational Data
              </h2>
              <p style={{ fontSize: "13px", color: "#7f1d1d", lineHeight: "1.5", marginBottom: "16px" }}>
                Wipes all telemetry readings, anomaly records, AI recommendations, and system activity logs for this organisation.
                <strong> Preserved:</strong> Organisation profile, Admin account, Facility Blocks, sensor configurations, baselines, and IoT devices.
              </p>

              <button
                type="button"
                onClick={() => setShowClearModal(true)}
                className="btn"
                style={{
                  background: "#dc2626",
                  color: "#ffffff",
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  border: "none",
                  padding: "10px 18px",
                  borderRadius: "8px",
                  cursor: "pointer",
                }}
              >
                <Trash2 size={16} /> Reset Organisation Data
              </button>
            </div>
          </div>
        </div>
          </>
        )}

        {/* Wards Tab Content for Municipality Admins */}
        {activeTab === "wards" && (
          <div className="card" style={{ borderLeft: "4px solid #0284c7" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
              <div>
                <h2 style={{ fontSize: "18px", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                  <MapPin size={18} color="#0284c7" /> Municipality Wards Management
                </h2>
                <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: "4px 0 0" }}>
                  Configure municipal wards as operational sub-units for monitoring and reporting.
                </p>
              </div>
              <button
                type="button"
                onClick={loadWards}
                disabled={wardLoading}
                className="btn btn-outline btn-sm"
                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                <RefreshCw size={13} className={wardLoading ? "spin" : ""} /> Refresh
              </button>
            </div>

            {/* Inline Add Ward Form */}
            <form onSubmit={handleAddWard} style={{ display: "flex", gap: "10px", marginBottom: "24px", flexWrap: "wrap" }}>
              <input
                type="text"
                value={newWardName}
                onChange={(e) => setNewWardName(e.target.value)}
                placeholder="Enter ward name (e.g. Ward 1 – North Zone, Central Ward)"
                className="form-input"
                style={{ flex: 1, minWidth: "240px", padding: "10px 14px", borderRadius: "8px", border: "1px solid var(--clr-border)" }}
                disabled={wardLoading}
              />
              <button
                type="submit"
                disabled={wardLoading || !newWardName.trim()}
                className="btn btn-primary"
                style={{ display: "inline-flex", alignItems: "center", gap: "6px", backgroundColor: "#0284c7", borderColor: "#0284c7" }}
              >
                <Plus size={16} /> Add Ward
              </button>
            </form>

            {/* Wards List */}
            {wardLoading && wards.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px", color: "var(--clr-text-muted)" }}>
                <RefreshCw size={24} className="spin" style={{ marginBottom: "8px", opacity: 0.5 }} />
                <p>Loading wards...</p>
              </div>
            ) : wards.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px", border: "1px dashed var(--clr-border)", borderRadius: "12px", color: "var(--clr-text-muted)" }}>
                <MapPin size={32} style={{ marginBottom: "8px", opacity: 0.3 }} />
                <p style={{ fontWeight: 600, fontSize: "15px" }}>No wards defined yet</p>
                <p style={{ fontSize: "13px", marginTop: "4px" }}>
                  Use the form above to add your municipality's first operational ward.
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {wards.map((ward) => (
                  <div
                    key={ward.block_id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "14px 16px",
                      background: "var(--clr-surface-2)",
                      border: "1px solid var(--clr-border)",
                      borderRadius: "10px",
                      gap: "12px",
                      flexWrap: "wrap",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "rgba(2, 132, 199, 0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <MapPin size={16} color="#0284c7" />
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--clr-text-primary)" }}>
                          {ward.block_name}
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontFamily: "monospace" }}>
                          ID: {ward.block_id}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "12px",
                          background: ward.is_active ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                          color: ward.is_active ? "#10b981" : "#ef4444",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        {ward.is_active ? <CheckCircle2 size={10} /> : <XCircle size={10} />}
                        {ward.is_active ? "Active" : "Inactive"}
                      </span>

                      {ward.is_active && (
                        <button
                          type="button"
                          onClick={() => handleDeactivateWard(ward.block_id)}
                          disabled={wardLoading}
                          className="btn btn-outline btn-sm"
                          style={{ color: "#ef4444", borderColor: "#fca5a5", padding: "4px 8px", fontSize: "12px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                          title="Deactivate Ward"
                        >
                          <Trash2 size={13} /> Deactivate
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {showClearModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.5)",
            zIndex: 10000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "480px",
              background: "var(--clr-surface, #ffffff)",
              borderRadius: "16px",
              padding: "28px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
              border: "1px solid var(--clr-border, #e5e7eb)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px", color: "#dc2626" }}>
              <AlertTriangle size={28} />
              <h3 style={{ fontSize: "20px", fontWeight: 800, margin: 0 }}>Confirm Data Reset</h3>
            </div>

            <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", lineHeight: 1.6, marginBottom: "20px" }}>
              Are you sure you want to clear all telemetry readings, anomaly history, and recommendations for this organisation?
              This operation is permanent and cannot be undone.
            </p>

            <div style={{ marginBottom: "24px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "14px", cursor: "pointer", fontWeight: 600 }}>
                <input
                  type="checkbox"
                  checked={clearConfirmed}
                  onChange={(e) => setClearConfirmed(e.target.checked)}
                  style={{ width: "18px", height: "18px", accentColor: "#dc2626" }}
                />
                <span>I understand this will permanently delete operational data.</span>
              </label>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
              <button
                type="button"
                className="btn btn-outline"
                disabled={clearing}
                onClick={() => {
                  setShowClearModal(false);
                  setClearConfirmed(false);
                }}
              >
                Cancel
              </button>

              <button
                type="button"
                disabled={!clearConfirmed || clearing}
                onClick={handleClearData}
                style={{
                  background: clearConfirmed && !clearing ? "#dc2626" : "#fca5a5",
                  color: "#ffffff",
                  border: "none",
                  padding: "10px 20px",
                  borderRadius: "8px",
                  fontWeight: 700,
                  cursor: clearConfirmed && !clearing ? "pointer" : "not-allowed",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                {clearing ? (
                  <>
                    <RefreshCw size={16} className="spin" /> Clearing Data...
                  </>
                ) : (
                  <>
                    <Trash2 size={16} /> Yes, Clear Data
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
