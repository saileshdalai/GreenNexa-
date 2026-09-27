"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import {
  X,
  Building2,
  UserCheck,
  Layers,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Trash2,
  Save,
  Loader2,
  Shield,
  MapPin,
  Activity,
} from "lucide-react";

interface BlockItem {
  block_id?: string;
  block_name: string;
}

interface SensorConfigItem {
  baseline: number;
  warning_threshold: number;
  critical_threshold: number;
  unit: string;
}

interface OrganisationEditModalProps {
  organisationId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const MODULE_OPTIONS = [
  { id: "energy", label: "Energy", icon: "⚡", description: "Power, voltage, kWh, main grid consumption" },
  { id: "water", label: "Water", icon: "💧", description: "Flow meters, tank levels, daily water usage" },
  { id: "waste", label: "Waste", icon: "🗑️", description: "Smart bin fill levels, organic & solid waste weight" },
  { id: "air_quality", label: "Air Quality", icon: "🌡️", description: "AQI, PM2.5, PM10, CO2, temperature & humidity" },
  { id: "traffic", label: "Traffic", icon: "🚗", description: "Vehicle count, campus entry/exit speed & congestion" },
  { id: "parking", label: "Parking", icon: "🅿️", description: "Slot occupancy, electric vehicle charging status" },
  { id: "assets", label: "Assets", icon: "🏢", description: "HVAC plant, generators, elevator uptime & maintenance" },
  { id: "safety", label: "Safety", icon: "🚨", description: "Fire alarms, smoke sensors, emergency exit events" },
  { id: "climate", label: "Climate", icon: "🌱", description: "Carbon footprint, solar generation, sustainability KPI" },
];

const FACILITY_TYPES = [
  "School",
  "College / University",
  "Hospital",
  "Municipality / Municipal Campus",
  "Industrial Estate",
  "Commercial Complex",
  "Public Sector Facility",
  "Research Institute",
  "Other Facility",
];

export function OrganisationEditModal({
  organisationId,
  isOpen,
  onClose,
  onSuccess,
}: OrganisationEditModalProps) {
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<"details" | "admin" | "blocks" | "modules" | "sensors">("details");
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);

  // Form states
  const [name, setName] = useState<string>("");
  const [ownershipType, setOwnershipType] = useState<"GOVERNMENT" | "PRIVATE">("PRIVATE");
  const [facilityType, setFacilityType] = useState<string>("School");
  const [facilityName, setFacilityName] = useState<string>("");
  const [state, setState] = useState<string>("");
  const [district, setDistrict] = useState<string>("");
  const [city, setCity] = useState<string>("");
  const [address, setAddress] = useState<string>("");
  const [orgCode, setOrgCode] = useState<string>("");

  const [adminName, setAdminName] = useState<string>("");
  const [adminPhone, setAdminPhone] = useState<string>("");
  const [adminEmail, setAdminEmail] = useState<string>("");
  const [adminUserId, setAdminUserId] = useState<string>("");

  const [blocks, setBlocks] = useState<BlockItem[]>([]);
  const [enabledModules, setEnabledModules] = useState<string[]>([]);
  const [sensorConfigs, setSensorConfigs] = useState<Record<string, SensorConfigItem>>({});

  useEffect(() => {
    if (!isOpen || !organisationId) return;

    let isMounted = true;
    setLoading(true);
    setActiveTab("details");

    api
      .get<any>(`/api/v1/super-admin/organisations/${organisationId}/full-config`)
      .then((data) => {
        if (!isMounted) return;
        setName(data.organisation_name || "");
        setOwnershipType(data.ownership_type === "GOVERNMENT" ? "GOVERNMENT" : "PRIVATE");
        setFacilityType(data.facility_type || "School");
        setFacilityName(data.facility_name || "");
        setState(data.state || "");
        setDistrict(data.district || "");
        setCity(data.city || "");
        setAddress(data.address || "");
        setOrgCode(data.org_code || "");

        setAdminName(data.admin_name || "");
        setAdminPhone(data.admin_phone || "");
        setAdminEmail(data.admin_email || "");
        setAdminUserId(data.admin_user_id || "");

        if (Array.isArray(data.blocks)) {
          setBlocks(data.blocks.map((b: any) => ({ block_id: b.block_id, block_name: b.block_name })));
        } else {
          setBlocks([]);
        }

        setEnabledModules(data.enabled_modules || []);
        setSensorConfigs(data.sensor_configs || {});
      })
      .catch((err: any) => {
        if (isMounted) {
          showToast(err.message || "Failed to load organisation configuration", "error");
          onClose();
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, organisationId]);

  if (!isOpen) return null;

  const toggleModule = (modId: string) => {
    setEnabledModules((prev) => {
      const next = prev.includes(modId) ? prev.filter((m) => m !== modId) : [...prev, modId];
      if (!prev.includes(modId) && !sensorConfigs[modId]) {
        // Provide default config when enabling new module
        setSensorConfigs((c) => ({
          ...c,
          [modId]: { baseline: 100, warning_threshold: 15, critical_threshold: 30, unit: "" },
        }));
      }
      return next;
    });
  };

  const handleUpdateSensorSetting = (
    modId: string,
    field: "baseline" | "warning_threshold" | "critical_threshold" | "unit",
    val: any
  ) => {
    setSensorConfigs((prev) => {
      const current = prev[modId] || { baseline: 100, warning_threshold: 15, critical_threshold: 30, unit: "" };
      return {
        ...prev,
        [modId]: {
          ...current,
          [field]: field === "unit" ? val : parseFloat(val) || 0,
        },
      };
    });
  };

  const handleAddBlock = () => {
    const nextIdx = blocks.length + 1;
    const bId = `BLK-${nextIdx < 10 ? "00" : nextIdx < 100 ? "0" : ""}${nextIdx}`;
    setBlocks((prev) => [...prev, { block_id: bId, block_name: `Block ${nextIdx}` }]);
  };

  const handleRemoveBlock = (index: number) => {
    if (blocks.length <= 1) {
      showToast("Organisation must retain at least 1 facility block.", "warning");
      return;
    }
    setBlocks((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateBlockName = (index: number, val: string) => {
    setBlocks((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], block_name: val };
      return next;
    });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      showToast("Organisation Name is required", "error");
      setActiveTab("details");
      return;
    }
    if (blocks.length === 0) {
      showToast("Please configure at least 1 facility block.", "error");
      setActiveTab("blocks");
      return;
    }
    if (blocks.some((b) => !b.block_name.trim())) {
      showToast("Block names cannot be empty.", "error");
      setActiveTab("blocks");
      return;
    }
    const blockNames = blocks.map((b) => b.block_name.trim().toLowerCase());
    if (new Set(blockNames).size !== blockNames.length) {
      showToast("Duplicate block names are not permitted.", "error");
      setActiveTab("blocks");
      return;
    }
    if (enabledModules.length === 0) {
      showToast("At least one operational module must be enabled.", "error");
      setActiveTab("modules");
      return;
    }

    // Validate sensor configs for enabled modules
    for (const mod of enabledModules) {
      const cfg = sensorConfigs[mod];
      if (cfg) {
        if (cfg.baseline <= 0) {
          showToast(`Baseline for ${mod} must be greater than 0.`, "error");
          setActiveTab("sensors");
          return;
        }
        if (cfg.warning_threshold > cfg.critical_threshold) {
          showToast(
            `Warning threshold (${cfg.warning_threshold}%) cannot exceed critical threshold (${cfg.critical_threshold}%) for ${mod}.`,
            "error"
          );
          setActiveTab("sensors");
          return;
        }
      }
    }

    setSaving(true);
    try {
      const payload = {
        name: name.trim(),
        ownership_type: ownershipType,
        facility_type: facilityType,
        facility_name: facilityName.trim() || name.trim(),
        state: state.trim() || undefined,
        district: district.trim() || undefined,
        city: city.trim() || undefined,
        address: address.trim() || undefined,
        org_code: orgCode.trim() || undefined,
        admin_name: adminName.trim() || undefined,
        admin_phone: adminPhone.trim() || undefined,
        blocks: blocks.map((b) => ({ block_id: b.block_id, block_name: b.block_name.trim() })),
        enabled_modules: enabledModules,
        sensor_configs: sensorConfigs,
      };

      await api.put(`/api/v1/super-admin/organisations/${organisationId}/edit-full`, payload);
      showToast(`Organisation ${name} configuration successfully updated. Historical records preserved.`, "success");
      onSuccess();
      onClose();
    } catch (err: any) {
      showToast(err.message || "Failed to update organisation configuration", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "20px",
      }}
    >
      <div
        style={{
          backgroundColor: "var(--clr-surface)",
          borderRadius: "16px",
          border: "1px solid var(--clr-border)",
          maxWidth: "880px",
          width: "100%",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
          overflow: "hidden",
        }}
      >
        {/* Header */}
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
                background: "var(--clr-primary-light)",
                color: "var(--clr-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Building2 size={22} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h3 style={{ fontSize: "17px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
                  Edit Organisation Configuration
                </h3>
                <span
                  style={{
                    fontFamily: "monospace",
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "2px 6px",
                    borderRadius: "4px",
                    background: "var(--clr-primary-light)",
                    color: "var(--clr-primary)",
                  }}
                >
                  {organisationId}
                </span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--clr-text-muted)", margin: 0, marginTop: "2px" }}>
                Atomic configuration update — all historical telemetry, anomalies, and recommendations are safely preserved.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              border: "none",
              background: "transparent",
              color: "var(--clr-text-muted)",
              cursor: "pointer",
              padding: "6px",
              borderRadius: "8px",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid var(--clr-border)",
            background: "var(--clr-surface)",
            padding: "0 16px",
            gap: "4px",
            overflowX: "auto",
          }}
        >
          {[
            { id: "details", label: "General Details", icon: <Building2 size={15} /> },
            { id: "admin", label: "Admin Contact", icon: <UserCheck size={15} /> },
            { id: "blocks", label: `Blocks (${blocks.length})`, icon: <Layers size={15} /> },
            { id: "modules", label: `Modules (${enabledModules.length})`, icon: <Activity size={15} /> },
            { id: "sensors", label: "Baselines & Thresholds", icon: <Sliders size={15} /> },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  border: "none",
                  borderBottom: isActive ? "2px solid var(--clr-primary)" : "2px solid transparent",
                  background: "transparent",
                  color: isActive ? "var(--clr-primary)" : "var(--clr-text-secondary)",
                  padding: "12px 14px",
                  fontSize: "13px",
                  fontWeight: isActive ? 700 : 500,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  whiteSpace: "nowrap",
                  transition: "all 0.15s ease",
                }}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Modal Body */}
        <div style={{ padding: "24px", overflowY: "auto", flex: 1 }}>
          {loading ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 0", gap: "12px" }}>
              <Loader2 size={32} className="spin" color="var(--clr-primary)" />
              <span style={{ fontSize: "14px", color: "var(--clr-text-muted)" }}>Loading current organisation configuration…</span>
            </div>
          ) : (
            <form id="edit-org-form" onSubmit={handleSave}>
              {/* TAB 1: DETAILS */}
              {activeTab === "details" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                  <div>
                    <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                      Organisation Ownership *
                    </label>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                      <button
                        type="button"
                        id="edit-ownership-government"
                        className="btn"
                        style={{
                          padding: "10px 14px",
                          borderRadius: "8px",
                          border: ownershipType === "GOVERNMENT" ? "2px solid #10b981" : "1px solid var(--clr-border, #334155)",
                          background: ownershipType === "GOVERNMENT" ? "rgba(16, 185, 129, 0.12)" : "var(--clr-surface, #1e293b)",
                          color: ownershipType === "GOVERNMENT" ? "#10b981" : "var(--clr-text-secondary, #94a3b8)",
                          fontWeight: 600,
                          fontSize: "13px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "8px",
                          transition: "all 0.15s ease",
                        }}
                        onClick={() => setOwnershipType("GOVERNMENT")}
                      >
                        <span>🏛️</span> Government
                      </button>
                      <button
                        type="button"
                        id="edit-ownership-private"
                        className="btn"
                        style={{
                          padding: "10px 14px",
                          borderRadius: "8px",
                          border: ownershipType === "PRIVATE" ? "2px solid #10b981" : "1px solid var(--clr-border, #334155)",
                          background: ownershipType === "PRIVATE" ? "rgba(16, 185, 129, 0.12)" : "var(--clr-surface, #1e293b)",
                          color: ownershipType === "PRIVATE" ? "#10b981" : "var(--clr-text-secondary, #94a3b8)",
                          fontWeight: 600,
                          fontSize: "13px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "8px",
                          transition: "all 0.15s ease",
                        }}
                        onClick={() => setOwnershipType("PRIVATE")}
                      >
                        <span>🏢</span> Private
                      </button>
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        Organisation Name *
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Apex Research Campus"
                        required
                        style={{ width: "100%" }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        Facility Type *
                      </label>
                      <select
                        className="form-input"
                        value={facilityType}
                        onChange={(e) => setFacilityType(e.target.value)}
                        style={{ width: "100%" }}
                      >
                        {FACILITY_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        Campus / Facility Name
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={facilityName}
                        onChange={(e) => setFacilityName(e.target.value)}
                        placeholder="e.g. North Innovation Campus"
                        style={{ width: "100%" }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        Org Code / Custom ID
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={orgCode}
                        onChange={(e) => setOrgCode(e.target.value)}
                        placeholder="e.g. APEX-01"
                        style={{ width: "100%" }}
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                      Street Address
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="e.g. 100 Innovation Way"
                      style={{ width: "100%" }}
                    />
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        City
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={city}
                        onChange={(e) => setCity(e.target.value)}
                        placeholder="e.g. Bengaluru"
                        style={{ width: "100%" }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        District
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={district}
                        onChange={(e) => setDistrict(e.target.value)}
                        placeholder="e.g. Bengaluru Urban"
                        style={{ width: "100%" }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        State
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={state}
                        onChange={(e) => setState(e.target.value)}
                        placeholder="e.g. Karnataka"
                        style={{ width: "100%" }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: ADMIN */}
              {activeTab === "admin" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                  <div
                    style={{
                      padding: "12px 16px",
                      borderRadius: "10px",
                      background: "rgba(16, 185, 129, 0.1)",
                      border: "1px solid rgba(16, 185, 129, 0.2)",
                      fontSize: "12px",
                      color: "var(--clr-text-secondary)",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >
                    <Shield size={18} color="#10b981" />
                    <span>
                      The primary administrator account manages day-to-day operations and receives critical alerts.
                    </span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        Admin Full Name
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={adminName}
                        onChange={(e) => setAdminName(e.target.value)}
                        placeholder="e.g. Dr. Jane Doe"
                        style={{ width: "100%" }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        Contact Phone
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={adminPhone}
                        onChange={(e) => setAdminPhone(e.target.value)}
                        placeholder="e.g. +91 9876543210"
                        style={{ width: "100%" }}
                      />
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        Admin Email (System Identifier)
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={adminEmail}
                        disabled
                        style={{ width: "100%", opacity: 0.7, cursor: "not-allowed" }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-secondary)", display: "block", marginBottom: "6px" }}>
                        Admin User ID (Immutable)
                      </label>
                      <input
                        type="text"
                        className="form-input"
                        value={adminUserId}
                        disabled
                        style={{ width: "100%", opacity: 0.7, cursor: "not-allowed" }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: BLOCKS */}
              {activeTab === "blocks" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      paddingBottom: "12px",
                      borderBottom: "1px solid var(--clr-border-light)",
                    }}
                  >
                    <div>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-text-primary)" }}>
                        Physical Facility Blocks
                      </span>
                      <p style={{ fontSize: "11px", color: "var(--clr-text-muted)", margin: "2px 0 0 0" }}>
                        Renaming blocks retains all historical telemetry. If a block is removed, historical data is safely preserved via soft-deactivation.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleAddBlock}
                      className="btn btn-outline btn-sm"
                      style={{ display: "flex", alignItems: "center", gap: "4px" }}
                    >
                      <Plus size={14} /> Add Block
                    </button>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    {blocks.map((blk, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                          padding: "10px 14px",
                          borderRadius: "10px",
                          background: "var(--clr-surface-2)",
                          border: "1px solid var(--clr-border-light)",
                        }}
                      >
                        <span
                          style={{
                            fontSize: "11px",
                            fontFamily: "monospace",
                            fontWeight: 700,
                            padding: "4px 8px",
                            borderRadius: "6px",
                            background: "var(--clr-surface)",
                            border: "1px solid var(--clr-border)",
                            color: "var(--clr-primary)",
                            minWidth: "75px",
                            textAlign: "center",
                          }}
                        >
                          {blk.block_id || `BLK-${idx + 1}`}
                        </span>

                        <input
                          type="text"
                          className="form-input"
                          value={blk.block_name}
                          onChange={(e) => handleUpdateBlockName(idx, e.target.value)}
                          placeholder="Block Name e.g. Academic Block"
                          style={{ flex: 1 }}
                          required
                        />

                        <button
                          type="button"
                          onClick={() => handleRemoveBlock(idx)}
                          className="btn btn-outline btn-sm"
                          style={{ color: "#ef4444", borderColor: "rgba(239, 68, 68, 0.3)", padding: "6px" }}
                          title="Remove block"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 4: MODULES */}
              {activeTab === "modules" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <p style={{ fontSize: "12px", color: "var(--clr-text-muted)", margin: 0 }}>
                    Select which sustainability modules are active for this facility. Telemetry streams and dashboard cards will reflect this selection.
                  </p>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "12px" }}>
                    {MODULE_OPTIONS.map((m) => {
                      const isChecked = enabledModules.includes(m.id);
                      return (
                        <div
                          key={m.id}
                          onClick={() => toggleModule(m.id)}
                          style={{
                            padding: "14px",
                            borderRadius: "12px",
                            border: isChecked ? "2px solid var(--clr-primary)" : "1px solid var(--clr-border)",
                            background: isChecked ? "var(--clr-primary-light)" : "var(--clr-surface-2)",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                            display: "flex",
                            alignItems: "flex-start",
                            gap: "12px",
                          }}
                        >
                          <span style={{ fontSize: "20px" }}>{m.icon}</span>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--clr-text-primary)" }}>
                                {m.label}
                              </span>
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => {}} // Handled by container
                                style={{ accentColor: "var(--clr-primary)", cursor: "pointer" }}
                              />
                            </div>
                            <p style={{ fontSize: "11px", color: "var(--clr-text-muted)", margin: "4px 0 0 0", lineHeight: 1.3 }}>
                              {m.description}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* TAB 5: SENSORS & THRESHOLDS */}
              {activeTab === "sensors" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                  <div
                    style={{
                      padding: "12px 16px",
                      borderRadius: "10px",
                      background: "rgba(59, 130, 246, 0.1)",
                      border: "1px solid rgba(59, 130, 246, 0.2)",
                      fontSize: "12px",
                      color: "var(--clr-text-secondary)",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                    }}
                  >
                    <Sliders size={18} color="#3b82f6" />
                    <span>
                      Specify expected normal operational baselines and deviation tolerance percentages (±%). Warning threshold must be strictly less than or equal to Critical threshold.
                    </span>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    {enabledModules.map((modId) => {
                      const modMeta = MODULE_OPTIONS.find((m) => m.id === modId) || { label: modId, icon: "📊" };
                      const cfg = sensorConfigs[modId] || { baseline: 100, warning_threshold: 15, critical_threshold: 30, unit: "" };
                      const isThresholdInvalid = cfg.warning_threshold > cfg.critical_threshold;

                      return (
                        <div
                          key={modId}
                          style={{
                            padding: "16px",
                            borderRadius: "12px",
                            background: "var(--clr-surface-2)",
                            border: isThresholdInvalid ? "1px solid #ef4444" : "1px solid var(--clr-border-light)",
                            display: "flex",
                            flexDirection: "column",
                            gap: "12px",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span style={{ fontSize: "18px" }}>{modMeta.icon}</span>
                              <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--clr-text-primary)" }}>
                                {modMeta.label}
                              </span>
                            </div>
                            {isThresholdInvalid && (
                              <span style={{ fontSize: "11px", color: "#ef4444", fontWeight: 700, display: "flex", alignItems: "center", gap: "4px" }}>
                                <AlertTriangle size={13} /> Warning % cannot exceed Critical %
                              </span>
                            )}
                          </div>

                          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
                            <div>
                              <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--clr-text-muted)", display: "block", marginBottom: "4px" }}>
                                Baseline Value
                              </label>
                              <input
                                type="number"
                                step="any"
                                min="0.01"
                                className="form-input"
                                value={cfg.baseline}
                                onChange={(e) => handleUpdateSensorSetting(modId, "baseline", e.target.value)}
                                style={{ width: "100%", fontSize: "12px" }}
                                required
                              />
                            </div>

                            <div>
                              <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--clr-text-muted)", display: "block", marginBottom: "4px" }}>
                                Measurement Unit
                              </label>
                              <input
                                type="text"
                                className="form-input"
                                value={cfg.unit || ""}
                                onChange={(e) => handleUpdateSensorSetting(modId, "unit", e.target.value)}
                                placeholder="e.g. kWh, L, AQI"
                                style={{ width: "100%", fontSize: "12px" }}
                              />
                            </div>

                            <div>
                              <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--clr-text-muted)", display: "block", marginBottom: "4px" }}>
                                Warning Tol. (±%)
                              </label>
                              <input
                                type="number"
                                step="any"
                                min="0"
                                max="100"
                                className="form-input"
                                value={cfg.warning_threshold}
                                onChange={(e) => handleUpdateSensorSetting(modId, "warning_threshold", e.target.value)}
                                style={{ width: "100%", fontSize: "12px" }}
                                required
                              />
                            </div>

                            <div>
                              <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--clr-text-muted)", display: "block", marginBottom: "4px" }}>
                                Critical Tol. (±%)
                              </label>
                              <input
                                type="number"
                                step="any"
                                min="0"
                                max="100"
                                className="form-input"
                                value={cfg.critical_threshold}
                                onChange={(e) => handleUpdateSensorSetting(modId, "critical_threshold", e.target.value)}
                                style={{ width: "100%", fontSize: "12px" }}
                                required
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </form>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--clr-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--clr-surface-2)",
          }}
        >
          <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>
            Changes will take effect immediately without downtime.
          </span>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button"
              onClick={onClose}
              className="btn btn-outline btn-sm"
              disabled={saving}
            >
              Cancel
            </button>

            <button
              type="submit"
              form="edit-org-form"
              className="btn btn-primary btn-sm"
              disabled={loading || saving}
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
            >
              {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />}
              <span>{saving ? "Saving Changes…" : "Save Configuration"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
