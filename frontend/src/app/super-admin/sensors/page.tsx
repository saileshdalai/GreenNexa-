"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { SensorConfigOverviewItem } from "@/types";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";
import {
  MASTER_SENSOR_CATALOG,
  SensorDefinition,
  getRecommendedSensorsForType,
  getDefaultConfigsForSensors,
  normalizeTypeKey,
} from "@/lib/sensorCatalog";
import {
  RadioTower,
  Save,
  RotateCcw,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  Activity,
  Sliders,
  Building2,
  ShieldAlert,
  Layers,
  Sparkles,
  Info,
  ChevronDown,
} from "lucide-react";

function SensorConfigurationContent() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const { isModuleUnread } = useNotifications();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [configs, setConfigs] = useState<SensorConfigOverviewItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [savingOrg, setSavingOrg] = useState<boolean>(false);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [sensorSearch, setSensorSearch] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"config" | "matrix">("config");

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const data = await api.get<SensorConfigOverviewItem[]>("/api/v1/super-admin/sensors");
      setConfigs(data);

      // Set initial selected organisation
      const queryOrgId = searchParams.get("org_id");
      if (queryOrgId && data.some((c) => c.organisation_id === queryOrgId)) {
        setSelectedOrgId(queryOrgId);
      } else if (data.length > 0 && !selectedOrgId) {
        setSelectedOrgId(data[0].organisation_id);
      }
    } catch (err: any) {
      showToast(err.message || "Failed to load sensor configurations", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadConfigs();
  }, [user]);

  // Current selected organisation config
  const selectedConfig = configs.find((c) => c.organisation_id === selectedOrgId);
  const detectedType = selectedConfig?.facility_type || "Facility";
  const recommendedSensorIds = getRecommendedSensorsForType(detectedType);

  // Group master catalog into Recommended vs Additional
  const recommendedSensors: SensorDefinition[] = [];
  const additionalSensors: SensorDefinition[] = [];

  MASTER_SENSOR_CATALOG.forEach((s) => {
    if (recommendedSensorIds.includes(s.id)) {
      recommendedSensors.push(s);
    } else {
      additionalSensors.push(s);
    }
  });

  // Filter sensors by search
  const filterSensors = (list: SensorDefinition[]) => {
    if (!sensorSearch.trim()) return list;
    const term = sensorSearch.toLowerCase();
    return list.filter(
      (s) =>
        s.name.toLowerCase().includes(term) ||
        s.metric.toLowerCase().includes(term) ||
        s.category.toLowerCase().includes(term) ||
        s.id.toLowerCase().includes(term)
    );
  };

  const filteredRecommended = filterSensors(recommendedSensors);
  const filteredAdditional = filterSensors(additionalSensors);

  // Check if a sensor is currently enabled
  const isSensorEnabled = (sensorId: string): boolean => {
    if (!selectedConfig) return false;
    const list = selectedConfig.enabled_modules || [];
    if (list.includes(sensorId)) return true;
    // Legacy alias check
    if (sensorId === "equipment_asset" && list.includes("assets")) return true;
    return false;
  };

  // Toggle a sensor ON / OFF
  const handleToggleSensor = (sensorId: string) => {
    if (!selectedConfig) return;
    setConfigs((prev) =>
      prev.map((c) => {
        if (c.organisation_id !== selectedConfig.organisation_id) return c;
        const currentList = c.enabled_modules || [];
        const isCurrentlyOn = currentList.includes(sensorId) || (sensorId === "equipment_asset" && currentList.includes("assets"));

        let nextList: string[];
        if (isCurrentlyOn) {
          nextList = currentList.filter((m) => m !== sensorId && !(sensorId === "equipment_asset" && m === "assets"));
        } else {
          nextList = [...currentList, sensorId];
        }

        return { ...c, enabled_modules: nextList };
      })
    );
  };

  // Update Baseline, Threshold, or Unit for a sensor
  const handleUpdateSensorSetting = (
    sensorId: string,
    field: "baseline" | "warning_threshold" | "critical_threshold" | "unit",
    val: any
  ) => {
    if (!selectedConfig) return;
    const def = MASTER_SENSOR_CATALOG.find((s) => s.id === sensorId);
    setConfigs((prev) =>
      prev.map((c) => {
        if (c.organisation_id !== selectedConfig.organisation_id) return c;
        const currentConfigs = c.sensor_configs || {};
        const existingSetting = currentConfigs[sensorId] || {
          baseline: def?.defaultBaseline ?? 100,
          warning_threshold: def?.defaultWarn ?? 15,
          critical_threshold: def?.defaultCrit ?? 30,
          unit: def?.unit ?? "",
        };

        const updatedSetting = {
          ...existingSetting,
          [field]: field === "unit" ? val : parseFloat(val) || 0,
        };

        return {
          ...c,
          sensor_configs: {
            ...currentConfigs,
            [sensorId]: updatedSetting,
          },
        };
      })
    );
  };

  // Reset to Recommended
  const handleResetToRecommended = () => {
    if (!selectedConfig) return;
    const defaultSettings = getDefaultConfigsForSensors(recommendedSensorIds);
    setConfigs((prev) =>
      prev.map((c) => {
        if (c.organisation_id !== selectedConfig.organisation_id) return c;
        return {
          ...c,
          enabled_modules: [...recommendedSensorIds],
          sensor_configs: {
            ...(c.sensor_configs || {}),
            ...defaultSettings,
          },
        };
      })
    );
    showToast(`Reset to recommended sensors for ${detectedType}`, "info");
  };

  // Save Configuration to Backend
  const handleSaveConfig = async () => {
    if (!selectedConfig) return;
    setSavingOrg(true);
    try {
      await api.put(`/api/v1/super-admin/sensors/${selectedConfig.organisation_id}`, {
        enabled_modules: selectedConfig.enabled_modules,
        sensor_configs: selectedConfig.sensor_configs || {},
      });
      showToast(`Updated sensor configuration for ${selectedConfig.organisation_name} (Historical data preserved)`, "success");
      loadConfigs();
    } catch (err: any) {
      showToast(err.message || "Failed to save sensor configuration", "error");
    } finally {
      setSavingOrg(false);
    }
  };

  return (
    <AppLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
            <RadioTower color="var(--clr-primary)" size={28} />
            Sensor Configuration & Control
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            Super Admin Single Source of Truth: Configure recommended default telemetry, turn individual sensors ON/OFF, and customize operational thresholds.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <div style={{ display: "flex", background: "var(--clr-surface-2)", borderRadius: "8px", padding: "3px", border: "1px solid var(--clr-border)" }}>
            <button
              onClick={() => setActiveTab("config")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 700,
                border: "none",
                cursor: "pointer",
                background: activeTab === "config" ? "var(--clr-primary)" : "transparent",
                color: activeTab === "config" ? "#ffffff" : "var(--clr-text-secondary)",
              }}
            >
              Interactive Editor
            </button>
            <button
              onClick={() => setActiveTab("matrix")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 700,
                border: "none",
                cursor: "pointer",
                background: activeTab === "matrix" ? "var(--clr-primary)" : "transparent",
                color: activeTab === "matrix" ? "#ffffff" : "var(--clr-text-secondary)",
              }}
            >
              Platform Matrix
            </button>
          </div>

          <button onClick={loadConfigs} className="btn btn-outline btn-sm" title="Refresh">
            <RefreshCw size={14} className={loading ? "spin" : ""} />
          </button>
        </div>
      </div>

      {activeTab === "config" ? (
        <>
          {/* Organisation Selection & Detected Type Banner */}
          <div className="card" style={{ padding: "20px", marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
              <div style={{ flex: "1 1 300px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: 700, color: "var(--clr-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                  Select Organisation / Facility
                </label>
                <div style={{ position: "relative" }}>
                  <Building2 size={16} color="var(--clr-text-muted)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
                  <select
                    className="form-input"
                    value={selectedOrgId}
                    onChange={(e) => setSelectedOrgId(e.target.value)}
                    style={{ paddingLeft: "36px", fontWeight: 700, fontSize: "14px" }}
                  >
                    {configs.map((c) => (
                      <option key={c.organisation_id} value={c.organisation_id}>
                        {c.organisation_name} ({c.facility_type}) — {c.organisation_id}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {selectedConfig && (
                <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 700, textTransform: "uppercase" }}>Detected Type</div>
                    <span
                      style={{
                        display: "inline-block",
                        marginTop: "4px",
                        padding: "4px 10px",
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontWeight: 800,
                        backgroundColor: "rgba(26, 122, 60, 0.1)",
                        color: "var(--clr-primary)",
                        border: "1px solid rgba(26, 122, 60, 0.25)",
                      }}
                    >
                      {detectedType}
                    </span>
                  </div>

                  <div>
                    <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 700, textTransform: "uppercase" }}>Data Source</div>
                    <span
                      style={{
                        display: "inline-block",
                        marginTop: "4px",
                        padding: "4px 10px",
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontWeight: 800,
                        backgroundColor: selectedConfig.data_source === "iot" ? "rgba(6, 182, 212, 0.15)" : "var(--clr-primary-light)",
                        color: selectedConfig.data_source === "iot" ? "#06b6d4" : "var(--clr-primary)",
                      }}
                    >
                      {selectedConfig.data_source.toUpperCase()}
                    </span>
                  </div>

                  <div>
                    <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 700, textTransform: "uppercase" }}>Active Sensors</div>
                    <div style={{ fontSize: "15px", fontWeight: 800, color: "var(--clr-text-primary)", marginTop: "2px" }}>
                      {selectedConfig.enabled_modules?.length || 0} / {MASTER_SENSOR_CATALOG.length}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Controls Bar: Search & Action Buttons */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
            <div style={{ position: "relative", width: "320px" }}>
              <Search size={15} color="var(--clr-text-muted)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
              <input
                type="text"
                className="form-input"
                placeholder="Search catalog sensors..."
                value={sensorSearch}
                onChange={(e) => setSensorSearch(e.target.value)}
                style={{ paddingLeft: "34px", fontSize: "13px" }}
              />
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                onClick={handleResetToRecommended}
                className="btn btn-outline"
                style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px" }}
                title="Restore default recommended sensor selection for this type"
              >
                <RotateCcw size={14} />
                Reset to Recommended
              </button>

              <button
                type="button"
                onClick={handleSaveConfig}
                disabled={savingOrg || !selectedConfig}
                className="btn btn-primary"
                style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px" }}
              >
                <Save size={14} />
                {savingOrg ? "Saving..." : "Save Configuration"}
              </button>
            </div>
          </div>

          {/* Section 1: Recommended Sensors for Detected Type */}
          <div className="card" style={{ padding: "20px", marginBottom: "28px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", borderBottom: "1px solid var(--clr-border)", paddingBottom: "12px" }}>
              <div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Sparkles size={18} color="var(--clr-primary)" />
                  Recommended Sensors for {detectedType}
                  <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "12px", background: "rgba(26, 122, 60, 0.12)", color: "var(--clr-primary)" }}>
                    Default Active ({recommendedSensors.length})
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>
                  These standard sensors are recommended for {detectedType}. You can toggle any sensor OFF or customize its thresholds.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "14px" }}>
              {filteredRecommended.map((sensor) => {
                const isEnabled = isSensorEnabled(sensor.id);
                const currentSetting = selectedConfig?.sensor_configs?.[sensor.id] || {
                  baseline: sensor.defaultBaseline,
                  warning_threshold: sensor.defaultWarn,
                  critical_threshold: sensor.defaultCrit,
                  unit: sensor.unit,
                };

                return (
                  <div
                    key={sensor.id}
                    data-testid={`sensor-catalog-${sensor.id}`}
                    style={{
                      padding: "16px",
                      borderRadius: "10px",
                      border: isEnabled ? "1.5px solid var(--clr-primary)" : "1px solid var(--clr-border)",
                      backgroundColor: isEnabled ? "var(--clr-surface)" : "var(--clr-surface-2)",
                      opacity: isEnabled ? 1 : 0.72,
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                      <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", flex: 1 }}>
                        <input
                          type="checkbox"
                          checked={isEnabled}
                          onChange={() => handleToggleSensor(sensor.id)}
                          style={{ width: "17px", height: "17px", accentColor: "var(--clr-primary)", cursor: "pointer" }}
                        />
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                              {sensor.name}
                            </span>
                            {(isModuleUnread(sensor.metric) || isModuleUnread(sensor.id)) && (
                              <RedDotIndicator size="sm" label={`${sensor.name} — unread anomaly`} />
                            )}
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>
                            {sensor.metric}
                          </div>
                        </div>
                      </label>

                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 700,
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: isEnabled ? "rgba(16, 185, 129, 0.12)" : "rgba(148, 163, 184, 0.12)",
                          color: isEnabled ? "#10b981" : "var(--clr-text-muted)",
                        }}
                      >
                        {isEnabled ? "ACTIVE" : "OFF"}
                      </span>
                    </div>

                    <div style={{ fontSize: "11px", color: "var(--clr-text-secondary)", marginBottom: "12px", lineHeight: "1.4" }}>
                      {sensor.description}
                    </div>

                    {/* Threshold Settings Inputs */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "8px", paddingTop: "10px", borderTop: "1px solid var(--clr-border-light)" }}>
                      <div>
                        <label style={{ fontSize: "10px", fontWeight: 700, color: "var(--clr-text-muted)", display: "block", marginBottom: "2px" }}>Unit</label>
                        <input
                          type="text"
                          className="form-input"
                          value={currentSetting.unit || sensor.unit}
                          onChange={(e) => handleUpdateSensorSetting(sensor.id, "unit", e.target.value)}
                          disabled={!isEnabled}
                          style={{ padding: "4px 6px", fontSize: "11px", textAlign: "center" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "10px", fontWeight: 700, color: "var(--clr-text-muted)", display: "block", marginBottom: "2px" }}>Baseline</label>
                        <input
                          type="number"
                          className="form-input"
                          value={currentSetting.baseline ?? sensor.defaultBaseline}
                          onChange={(e) => handleUpdateSensorSetting(sensor.id, "baseline", e.target.value)}
                          disabled={!isEnabled}
                          style={{ padding: "4px 6px", fontSize: "11px", textAlign: "center" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "10px", fontWeight: 700, color: "var(--clr-text-muted)", display: "block", marginBottom: "2px" }}>Warn %</label>
                        <input
                          type="number"
                          className="form-input"
                          value={currentSetting.warning_threshold ?? sensor.defaultWarn}
                          onChange={(e) => handleUpdateSensorSetting(sensor.id, "warning_threshold", e.target.value)}
                          disabled={!isEnabled}
                          style={{ padding: "4px 6px", fontSize: "11px", textAlign: "center" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "10px", fontWeight: 700, color: "var(--clr-text-muted)", display: "block", marginBottom: "2px" }}>Crit %</label>
                        <input
                          type="number"
                          className="form-input"
                          value={currentSetting.critical_threshold ?? sensor.defaultCrit}
                          onChange={(e) => handleUpdateSensorSetting(sensor.id, "critical_threshold", e.target.value)}
                          disabled={!isEnabled}
                          style={{ padding: "4px 6px", fontSize: "11px", textAlign: "center" }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 2: Additional Available Sensors from Master Catalog */}
          <div className="card" style={{ padding: "20px", marginBottom: "28px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", borderBottom: "1px solid var(--clr-border)", paddingBottom: "12px" }}>
              <div>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Layers size={18} color="var(--clr-text-secondary)" />
                  Additional Available Sensors
                  <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", borderRadius: "12px", background: "var(--clr-surface-2)", color: "var(--clr-text-muted)" }}>
                    Optional ({additionalSensors.length})
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>
                  You can optionally turn ON any of these specialized municipal, asset, or industrial sensors.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "14px" }}>
              {filteredAdditional.map((sensor) => {
                const isEnabled = isSensorEnabled(sensor.id);
                const currentSetting = selectedConfig?.sensor_configs?.[sensor.id] || {
                  baseline: sensor.defaultBaseline,
                  warning_threshold: sensor.defaultWarn,
                  critical_threshold: sensor.defaultCrit,
                  unit: sensor.unit,
                };

                return (
                  <div
                    key={sensor.id}
                    style={{
                      padding: "16px",
                      borderRadius: "10px",
                      border: isEnabled ? "1.5px solid var(--clr-primary)" : "1px solid var(--clr-border)",
                      backgroundColor: isEnabled ? "var(--clr-surface)" : "var(--clr-surface-2)",
                      opacity: isEnabled ? 1 : 0.65,
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                      <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", flex: 1 }}>
                        <input
                          type="checkbox"
                          checked={isEnabled}
                          onChange={() => handleToggleSensor(sensor.id)}
                          style={{ width: "17px", height: "17px", accentColor: "var(--clr-primary)", cursor: "pointer" }}
                        />
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
                              {sensor.name}
                            </span>
                            {(isModuleUnread(sensor.metric) || isModuleUnread(sensor.id)) && (
                              <RedDotIndicator size="sm" label={`${sensor.name} — unread anomaly`} />
                            )}
                            <span style={{ fontSize: "9px", fontWeight: 700, padding: "1px 5px", borderRadius: "4px", background: "var(--clr-surface-2)", color: "var(--clr-text-muted)" }}>
                              {sensor.category}
                            </span>
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>
                            {sensor.metric}
                          </div>
                        </div>
                      </label>

                      <span
                        style={{
                          fontSize: "10px",
                          fontWeight: 700,
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: isEnabled ? "rgba(16, 185, 129, 0.12)" : "rgba(148, 163, 184, 0.12)",
                          color: isEnabled ? "#10b981" : "var(--clr-text-muted)",
                        }}
                      >
                        {isEnabled ? "ACTIVE" : "OFF"}
                      </span>
                    </div>

                    <div style={{ fontSize: "11px", color: "var(--clr-text-secondary)", marginBottom: "12px", lineHeight: "1.4" }}>
                      {sensor.description}
                    </div>

                    {/* Threshold Settings Inputs */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "8px", paddingTop: "10px", borderTop: "1px solid var(--clr-border-light)" }}>
                      <div>
                        <label style={{ fontSize: "10px", fontWeight: 700, color: "var(--clr-text-muted)", display: "block", marginBottom: "2px" }}>Unit</label>
                        <input
                          type="text"
                          className="form-input"
                          value={currentSetting.unit || sensor.unit}
                          onChange={(e) => handleUpdateSensorSetting(sensor.id, "unit", e.target.value)}
                          disabled={!isEnabled}
                          style={{ padding: "4px 6px", fontSize: "11px", textAlign: "center" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "10px", fontWeight: 700, color: "var(--clr-text-muted)", display: "block", marginBottom: "2px" }}>Baseline</label>
                        <input
                          type="number"
                          className="form-input"
                          value={currentSetting.baseline ?? sensor.defaultBaseline}
                          onChange={(e) => handleUpdateSensorSetting(sensor.id, "baseline", e.target.value)}
                          disabled={!isEnabled}
                          style={{ padding: "4px 6px", fontSize: "11px", textAlign: "center" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "10px", fontWeight: 700, color: "var(--clr-text-muted)", display: "block", marginBottom: "2px" }}>Warn %</label>
                        <input
                          type="number"
                          className="form-input"
                          value={currentSetting.warning_threshold ?? sensor.defaultWarn}
                          onChange={(e) => handleUpdateSensorSetting(sensor.id, "warning_threshold", e.target.value)}
                          disabled={!isEnabled}
                          style={{ padding: "4px 6px", fontSize: "11px", textAlign: "center" }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: "10px", fontWeight: 700, color: "var(--clr-text-muted)", display: "block", marginBottom: "2px" }}>Crit %</label>
                        <input
                          type="number"
                          className="form-input"
                          value={currentSetting.critical_threshold ?? sensor.defaultCrit}
                          onChange={(e) => handleUpdateSensorSetting(sensor.id, "critical_threshold", e.target.value)}
                          disabled={!isEnabled}
                          style={{ padding: "4px 6px", fontSize: "11px", textAlign: "center" }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      ) : (
        /* Matrix View (Platform Overview across all organisations) */
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
              <thead>
                <tr style={{ background: "var(--clr-surface-2)", borderBottom: "2px solid var(--clr-border)", textAlign: "left", color: "var(--clr-text-muted)", fontSize: "12px", fontWeight: 700, textTransform: "uppercase" }}>
                  <th style={{ padding: "14px 20px" }}>Organisation</th>
                  <th style={{ padding: "14px 20px" }}>Type</th>
                  <th style={{ padding: "14px 20px" }}>Data Source</th>
                  <th style={{ padding: "14px 20px" }}>Active Sensors</th>
                  <th style={{ padding: "14px 20px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {configs.map((c) => (
                  <tr key={c.organisation_id} style={{ borderBottom: "1px solid var(--clr-border-light)" }} className="table-row-hover">
                    <td style={{ padding: "16px 20px" }}>
                      <div style={{ fontWeight: 800, fontSize: "14px", color: "var(--clr-text-primary)" }}>{c.organisation_name}</div>
                      <div style={{ fontSize: "11px", color: "var(--clr-primary)", fontFamily: "monospace", fontWeight: 700 }}>{c.organisation_id}</div>
                    </td>
                    <td style={{ padding: "16px 20px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)" }}>{c.facility_type}</span>
                    </td>
                    <td style={{ padding: "16px 20px" }}>
                      <span style={{ fontSize: "11px", fontWeight: 800, padding: "3px 8px", borderRadius: "6px", background: c.data_source === "iot" ? "rgba(6, 182, 212, 0.15)" : "var(--clr-primary-light)", color: c.data_source === "iot" ? "#06b6d4" : "var(--clr-primary)" }}>
                        {c.data_source.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: "16px 20px" }}>
                      <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", maxWidth: "400px" }}>
                        {(c.enabled_modules || []).map((m) => (
                          <span
                            key={m}
                            style={{
                              fontSize: "11px",
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: "4px",
                              background: "rgba(26, 122, 60, 0.1)",
                              color: "var(--clr-primary)",
                            }}
                          >
                            {m.replace("_", " ")}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ padding: "16px 20px", textAlign: "right" }}>
                      <button
                        onClick={() => {
                          setSelectedOrgId(c.organisation_id);
                          setActiveTab("config");
                        }}
                        className="btn btn-outline btn-sm"
                        style={{ fontSize: "12px" }}
                      >
                        <Sliders size={13} />
                        Configure
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppLayout>
  );
}

export default function SensorConfigurationPage() {
  return (
    <Suspense fallback={<div style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>Loading sensor configuration...</div>}>
      <SensorConfigurationContent />
    </Suspense>
  );
}
