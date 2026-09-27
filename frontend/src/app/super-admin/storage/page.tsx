"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { StorageOverviewResponse, OrganisationStorageItem } from "@/types";
import {
  Database,
  HardDrive,
  RefreshCw,
  Search,
  Building2,
  Shield,
  Layers,
  Activity,
  AlertCircle,
  Lightbulb,
  Cpu,
  ArrowUpDown,
  CheckCircle,
} from "lucide-react";

export default function SuperAdminStoragePage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [storageData, setStorageData] = useState<StorageOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [ownershipFilter, setOwnershipFilter] = useState<"ALL" | "GOVERNMENT" | "PRIVATE">("ALL");
  const [sortBy, setSortBy] = useState<"usage" | "name">("usage");
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  const loadStorage = async (silent: boolean = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await api.get<StorageOverviewResponse>("/api/v1/super-admin/storage");
      setStorageData(data);
    } catch (err: any) {
      if (err.status === 403 || err.response?.status === 403) {
        showToast("Access denied: Super Admin role required", "error");
        router.push("/dashboard");
        return;
      }
      showToast(err.message || "Failed to load database storage overview", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadStorage();
  }, [user]);

  // Split and filter organisations
  const { govOrgs, privateOrgs, filteredTotalGovBytes, filteredTotalPrivateBytes } = useMemo(() => {
    if (!storageData) {
      return {
        govOrgs: [],
        privateOrgs: [],
        filteredTotalGovBytes: 0,
        filteredTotalPrivateBytes: 0,
      };
    }

    const term = searchTerm.trim().toLowerCase();

    let list = storageData.organisations.filter((org) => {
      const matchesSearch =
        !term ||
        org.organisation_name.toLowerCase().includes(term) ||
        org.organisation_id.toLowerCase().includes(term);

      const matchesFilter =
        ownershipFilter === "ALL" ||
        org.ownership_type.toUpperCase() === ownershipFilter;

      return matchesSearch && matchesFilter;
    });

    list.sort((a, b) => {
      if (sortBy === "usage") {
        return sortAsc
          ? a.logical_storage_bytes - b.logical_storage_bytes
          : b.logical_storage_bytes - a.logical_storage_bytes;
      }
      return sortAsc
        ? a.organisation_name.localeCompare(b.organisation_name)
        : b.organisation_name.localeCompare(a.organisation_name);
    });

    const gov = list.filter((o) => o.ownership_type.toUpperCase() === "GOVERNMENT");
    const priv = list.filter((o) => o.ownership_type.toUpperCase() === "PRIVATE");

    const govBytes = gov.reduce((acc, curr) => acc + curr.logical_storage_bytes, 0);
    const privBytes = priv.reduce((acc, curr) => acc + curr.logical_storage_bytes, 0);

    return {
      govOrgs: gov,
      privateOrgs: priv,
      filteredTotalGovBytes: govBytes,
      filteredTotalPrivateBytes: privBytes,
    };
  }, [storageData, searchTerm, ownershipFilter, sortBy, sortAsc]);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  return (
    <AppLayout>
      <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "24px 16px" }}>
        {/* Header Bar */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "16px",
            marginBottom: "24px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
              <span
                style={{
                  padding: "6px 10px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(16, 185, 129, 0.12)",
                  color: "var(--clr-primary, #10b981)",
                  display: "inline-flex",
                  alignItems: "center",
                }}
              >
                <Database size={20} />
              </span>
              <h1 style={{ fontSize: "24px", fontWeight: 800, margin: 0 }}>Manage Storage</h1>
            </div>
            <p style={{ margin: 0, fontSize: "14px", color: "var(--clr-text-secondary)" }}>
              Actual physical SQLite database file size and organisation-attributed logical operational footprint
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => loadStorage(false)}
              disabled={loading}
              id="storage-refresh-button"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
            >
              <RefreshCw size={15} className={loading ? "spin" : ""} />
              {loading ? "Measuring..." : "Refresh Storage"}
            </button>
          </div>
        </div>

        {/* Database Physical Storage Summary Card */}
        <div
          className="card"
          style={{
            padding: "24px",
            marginBottom: "24px",
            background: "var(--clr-surface-1, #1e293b)",
            border: "1px solid var(--clr-border, rgba(255, 255, 255, 0.1))",
            borderRadius: "14px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "12px",
              marginBottom: "20px",
              paddingBottom: "14px",
              borderBottom: "1px solid var(--clr-border, rgba(255, 255, 255, 0.08))",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <HardDrive size={18} style={{ color: "var(--clr-primary, #10b981)" }} />
              <h2 style={{ fontSize: "17px", fontWeight: 700, margin: 0 }}>Database Storage Overview</h2>
            </div>
            <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)" }}>
              Engine: <strong style={{ color: "var(--clr-text-primary)" }}>{storageData?.database_engine || "SQLite"}</strong>
              {storageData?.generated_at && (
                <span style={{ marginLeft: "12px" }}>
                  Last Measured: <strong style={{ color: "var(--clr-text-primary)" }}>{new Date(storageData.generated_at).toLocaleTimeString()}</strong>
                </span>
              )}
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "16px",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                padding: "16px",
                borderRadius: "10px",
                background: "var(--clr-surface-2, #0f172a)",
                border: "1px solid var(--clr-border, rgba(255, 255, 255, 0.06))",
              }}
            >
              <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginBottom: "6px" }}>
                Database File Size (Actual)
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--clr-primary, #10b981)" }}>
                {storageData?.database_size_formatted || "Calculating..."}
              </div>
              <div style={{ fontSize: "11px", color: "var(--clr-text-muted, #94a3b8)", marginTop: "4px" }}>
                {storageData ? `${storageData.database_size_bytes.toLocaleString()} bytes on disk` : ""}
              </div>
            </div>

            <div
              style={{
                padding: "16px",
                borderRadius: "10px",
                background: "var(--clr-surface-2, #0f172a)",
                border: "1px solid var(--clr-border, rgba(255, 255, 255, 0.06))",
              }}
            >
              <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginBottom: "6px" }}>
                Allocated / Host Disk
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "var(--clr-text-primary, #f8fafc)" }}>
                {storageData?.total_allocated_formatted || "N/A"}
              </div>
              <div style={{ fontSize: "11px", color: "var(--clr-text-muted, #94a3b8)", marginTop: "4px" }}>
                Host volume storage capacity
              </div>
            </div>

            <div
              style={{
                padding: "16px",
                borderRadius: "10px",
                background: "var(--clr-surface-2, #0f172a)",
                border: "1px solid var(--clr-border, rgba(255, 255, 255, 0.06))",
              }}
            >
              <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginBottom: "6px" }}>
                Remaining / Available Space
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "#38bdf8" }}>
                {storageData?.available_formatted || "N/A"}
              </div>
              <div style={{ fontSize: "11px", color: "var(--clr-text-muted, #94a3b8)", marginTop: "4px" }}>
                Host disk free capacity
              </div>
            </div>

            <div
              style={{
                padding: "16px",
                borderRadius: "10px",
                background: "var(--clr-surface-2, #0f172a)",
                border: "1px solid var(--clr-border, rgba(255, 255, 255, 0.06))",
              }}
            >
              <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginBottom: "6px" }}>
                Disk Usage %
              </div>
              <div style={{ fontSize: "26px", fontWeight: 800, color: "#f59e0b" }}>
                {storageData?.usage_percentage !== undefined && storageData?.usage_percentage !== null
                  ? `${storageData.usage_percentage}%`
                  : "N/A"}
              </div>
              {storageData?.usage_percentage !== undefined && storageData?.usage_percentage !== null && (
                <div
                  style={{
                    width: "100%",
                    height: "6px",
                    backgroundColor: "rgba(255,255,255,0.1)",
                    borderRadius: "3px",
                    marginTop: "8px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(storageData.usage_percentage, 100)}%`,
                      height: "100%",
                      backgroundColor: "#f59e0b",
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          {storageData?.database_path && (
            <div
              style={{
                fontSize: "12px",
                color: "var(--clr-text-secondary)",
                background: "rgba(0,0,0,0.2)",
                padding: "8px 12px",
                borderRadius: "6px",
                wordBreak: "break-all",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <span style={{ fontWeight: 600, color: "var(--clr-text-muted)" }}>Active DB Path:</span>
              <code>{storageData.database_path}</code>
            </div>
          )}
        </div>

        {/* Honest Accounting Banner */}
        <div
          style={{
            padding: "14px 18px",
            borderRadius: "10px",
            backgroundColor: "rgba(14, 165, 233, 0.08)",
            border: "1px solid rgba(14, 165, 233, 0.25)",
            marginBottom: "24px",
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
          }}
        >
          <AlertCircle size={18} style={{ color: "#38bdf8", flexShrink: 0, marginTop: "2px" }} />
          <div style={{ fontSize: "13px", lineHeight: 1.5, color: "var(--clr-text-secondary)" }}>
            <strong style={{ color: "var(--clr-text-primary)" }}>Storage Accounting Architecture:</strong>{" "}
            The <strong>Database File Size</strong> reflects the physical SQLite file on disk. SQLite files do not attribute disk pages to specific tenants. Organisation-level storage is calculated as an honest <strong>Organisation Data Usage (logical estimate)</strong> based on the exact record footprints of stored telemetry readings, anomaly logs, AI recommendations, IoT devices, blocks, and operational messages.
          </div>
        </div>

        {/* Totals Summary Cards (Government vs Private) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "16px",
            marginBottom: "24px",
          }}
        >
          <div
            className="card"
            style={{
              padding: "20px",
              background: "linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, rgba(14, 165, 233, 0.02) 100%)",
              border: "1px solid rgba(14, 165, 233, 0.25)",
              borderRadius: "12px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Government Total (Logical)
              </span>
              <span
                style={{
                  fontSize: "11px",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(14, 165, 233, 0.15)",
                  color: "#38bdf8",
                  fontWeight: 600,
                }}
              >
                {govOrgs.length} orgs
              </span>
            </div>
            <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
              {storageData ? storageData.government_total_logical_formatted : "0 B"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
              {storageData ? `${storageData.government_total_logical_bytes.toLocaleString()} bytes logical` : ""}
            </div>
          </div>

          <div
            className="card"
            style={{
              padding: "20px",
              background: "linear-gradient(135deg, rgba(168, 85, 247, 0.08) 0%, rgba(168, 85, 247, 0.02) 100%)",
              border: "1px solid rgba(168, 85, 247, 0.25)",
              borderRadius: "12px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "#c084fc", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Private Total (Logical)
              </span>
              <span
                style={{
                  fontSize: "11px",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(168, 85, 247, 0.15)",
                  color: "#c084fc",
                  fontWeight: 600,
                }}
              >
                {privateOrgs.length} orgs
              </span>
            </div>
            <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
              {storageData ? storageData.private_total_logical_formatted : "0 B"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
              {storageData ? `${storageData.private_total_logical_bytes.toLocaleString()} bytes logical` : ""}
            </div>
          </div>

          <div
            className="card"
            style={{
              padding: "20px",
              background: "linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.02) 100%)",
              border: "1px solid rgba(16, 185, 129, 0.25)",
              borderRadius: "12px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-primary, #10b981)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Combined Logical Total
              </span>
              <span
                style={{
                  fontSize: "11px",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(16, 185, 129, 0.15)",
                  color: "var(--clr-primary, #10b981)",
                  fontWeight: 600,
                }}
              >
                {storageData?.organisations.length || 0} orgs total
              </span>
            </div>
            <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)" }}>
              {storageData ? storageData.total_logical_formatted : "0 B"}
            </div>
            <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
              {storageData ? `${storageData.total_logical_bytes.toLocaleString()} bytes logical` : ""}
            </div>
          </div>
        </div>

        {/* Filter and Search Controls */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "12px",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: "1", minWidth: "260px", maxWidth: "420px" }}>
            <div style={{ position: "relative", width: "100%" }}>
              <Search
                size={16}
                style={{
                  position: "absolute",
                  left: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--clr-text-secondary)",
                }}
              />
              <input
                type="text"
                className="form-input"
                placeholder="Search by organisation name or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{
                  width: "100%",
                  paddingLeft: "36px",
                  paddingRight: "12px",
                  height: "38px",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <div style={{ display: "inline-flex", borderRadius: "8px", padding: "3px", backgroundColor: "var(--clr-surface-2, #0f172a)" }}>
              <button
                type="button"
                onClick={() => setOwnershipFilter("ALL")}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  border: "none",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  backgroundColor: ownershipFilter === "ALL" ? "var(--clr-primary, #10b981)" : "transparent",
                  color: ownershipFilter === "ALL" ? "#ffffff" : "var(--clr-text-secondary)",
                }}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setOwnershipFilter("GOVERNMENT")}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  border: "none",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  backgroundColor: ownershipFilter === "GOVERNMENT" ? "#0284c7" : "transparent",
                  color: ownershipFilter === "GOVERNMENT" ? "#ffffff" : "var(--clr-text-secondary)",
                }}
              >
                Government
              </button>
              <button
                type="button"
                onClick={() => setOwnershipFilter("PRIVATE")}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  border: "none",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  backgroundColor: ownershipFilter === "PRIVATE" ? "#9333ea" : "transparent",
                  color: ownershipFilter === "PRIVATE" ? "#ffffff" : "var(--clr-text-secondary)",
                }}
              >
                Private
              </button>
            </div>

            <button
              type="button"
              className="btn btn-outline btn-sm"
              onClick={() => {
                if (sortBy === "usage") {
                  setSortAsc(!sortAsc);
                } else {
                  setSortBy("usage");
                  setSortAsc(false);
                }
              }}
              style={{ fontSize: "12px", display: "inline-flex", alignItems: "center", gap: "6px" }}
              title="Sort by Storage Usage"
            >
              <ArrowUpDown size={13} />
              Sort by Usage {sortBy === "usage" ? (sortAsc ? "↑" : "↓") : ""}
            </button>
          </div>
        </div>

        {/* Section 1: Government Organisations */}
        {(ownershipFilter === "ALL" || ownershipFilter === "GOVERNMENT") && (
          <div className="card" style={{ padding: "20px", marginBottom: "24px", borderRadius: "12px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
                paddingBottom: "12px",
                borderBottom: "1px solid var(--clr-border, rgba(255, 255, 255, 0.08))",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span
                  style={{
                    padding: "4px 8px",
                    borderRadius: "6px",
                    backgroundColor: "rgba(14, 165, 233, 0.15)",
                    color: "#38bdf8",
                    fontSize: "12px",
                    fontWeight: 700,
                  }}
                >
                  GOVERNMENT
                </span>
                <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>Government Organisations</h3>
              </div>
              <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)" }}>
                Government Total: <strong style={{ color: "#38bdf8" }}>{formatBytes(filteredTotalGovBytes)}</strong>
              </div>
            </div>

            {govOrgs.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", color: "var(--clr-text-secondary)", fontSize: "14px" }}>
                No government organisations found matching filters.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--clr-border)", textAlign: "left", color: "var(--clr-text-secondary)" }}>
                      <th style={{ padding: "10px 12px" }}>Organisation</th>
                      <th style={{ padding: "10px 12px" }}>Ownership</th>
                      <th style={{ padding: "10px 12px" }}>Data Usage (Logical)</th>
                      <th style={{ padding: "10px 12px" }}>% of Total</th>
                      <th style={{ padding: "10px 12px" }}>Operational Footprint</th>
                    </tr>
                  </thead>
                  <tbody>
                    {govOrgs.map((org) => (
                      <tr key={org.organisation_id} style={{ borderBottom: "1px solid var(--clr-border, rgba(255, 255, 255, 0.05))" }}>
                        <td style={{ padding: "12px" }}>
                          <div style={{ fontWeight: 700, color: "var(--clr-text-primary)" }}>{org.organisation_name}</div>
                          <div style={{ fontSize: "11px", color: "var(--clr-text-secondary)", fontFamily: "monospace" }}>{org.organisation_id}</div>
                        </td>
                        <td style={{ padding: "12px" }}>
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: "10px",
                              fontSize: "11px",
                              fontWeight: 700,
                              backgroundColor: "rgba(14, 165, 233, 0.12)",
                              color: "#38bdf8",
                            }}
                          >
                            GOVERNMENT
                          </span>
                        </td>
                        <td style={{ padding: "12px" }}>
                          <div style={{ fontWeight: 700, color: "var(--clr-text-primary)" }}>
                            {org.logical_storage_formatted}
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>
                            {org.logical_storage_bytes.toLocaleString()} bytes
                          </div>
                        </td>
                        <td style={{ padding: "12px", minWidth: "120px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <div style={{ flex: 1, height: "6px", backgroundColor: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                              <div style={{ width: `${Math.min(org.percentage_of_total, 100)}%`, height: "100%", backgroundColor: "#38bdf8" }} />
                            </div>
                            <span style={{ fontSize: "12px", fontWeight: 600, minWidth: "36px" }}>
                              {org.percentage_of_total}%
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: "12px" }}>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(255,255,255,0.06)",
                                color: "var(--clr-text-secondary)",
                              }}
                            >
                              {org.readings_count.toLocaleString()} readings
                            </span>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(255,255,255,0.06)",
                                color: "var(--clr-text-secondary)",
                              }}
                            >
                              {org.anomalies_count} anomalies
                            </span>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(255,255,255,0.06)",
                                color: "var(--clr-text-secondary)",
                              }}
                            >
                              {org.recommendations_count} recs
                            </span>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(255,255,255,0.06)",
                                color: "var(--clr-text-secondary)",
                              }}
                            >
                              {org.blocks_count} blks / {org.devices_count} devs
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Section 2: Private Organisations */}
        {(ownershipFilter === "ALL" || ownershipFilter === "PRIVATE") && (
          <div className="card" style={{ padding: "20px", borderRadius: "12px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
                paddingBottom: "12px",
                borderBottom: "1px solid var(--clr-border, rgba(255, 255, 255, 0.08))",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span
                  style={{
                    padding: "4px 8px",
                    borderRadius: "6px",
                    backgroundColor: "rgba(168, 85, 247, 0.15)",
                    color: "#c084fc",
                    fontSize: "12px",
                    fontWeight: 700,
                  }}
                >
                  PRIVATE
                </span>
                <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>Private Organisations</h3>
              </div>
              <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)" }}>
                Private Total: <strong style={{ color: "#c084fc" }}>{formatBytes(filteredTotalPrivateBytes)}</strong>
              </div>
            </div>

            {privateOrgs.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", color: "var(--clr-text-secondary)", fontSize: "14px" }}>
                No private organisations found matching filters.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--clr-border)", textAlign: "left", color: "var(--clr-text-secondary)" }}>
                      <th style={{ padding: "10px 12px" }}>Organisation</th>
                      <th style={{ padding: "10px 12px" }}>Ownership</th>
                      <th style={{ padding: "10px 12px" }}>Data Usage (Logical)</th>
                      <th style={{ padding: "10px 12px" }}>% of Total</th>
                      <th style={{ padding: "10px 12px" }}>Operational Footprint</th>
                    </tr>
                  </thead>
                  <tbody>
                    {privateOrgs.map((org) => (
                      <tr key={org.organisation_id} style={{ borderBottom: "1px solid var(--clr-border, rgba(255, 255, 255, 0.05))" }}>
                        <td style={{ padding: "12px" }}>
                          <div style={{ fontWeight: 700, color: "var(--clr-text-primary)" }}>{org.organisation_name}</div>
                          <div style={{ fontSize: "11px", color: "var(--clr-text-secondary)", fontFamily: "monospace" }}>{org.organisation_id}</div>
                        </td>
                        <td style={{ padding: "12px" }}>
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: "10px",
                              fontSize: "11px",
                              fontWeight: 700,
                              backgroundColor: "rgba(168, 85, 247, 0.12)",
                              color: "#c084fc",
                            }}
                          >
                            PRIVATE
                          </span>
                        </td>
                        <td style={{ padding: "12px" }}>
                          <div style={{ fontWeight: 700, color: "var(--clr-text-primary)" }}>
                            {org.logical_storage_formatted}
                          </div>
                          <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>
                            {org.logical_storage_bytes.toLocaleString()} bytes
                          </div>
                        </td>
                        <td style={{ padding: "12px", minWidth: "120px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <div style={{ flex: 1, height: "6px", backgroundColor: "rgba(255,255,255,0.1)", borderRadius: "3px", overflow: "hidden" }}>
                              <div style={{ width: `${Math.min(org.percentage_of_total, 100)}%`, height: "100%", backgroundColor: "#c084fc" }} />
                            </div>
                            <span style={{ fontSize: "12px", fontWeight: 600, minWidth: "36px" }}>
                              {org.percentage_of_total}%
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: "12px" }}>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(255,255,255,0.06)",
                                color: "var(--clr-text-secondary)",
                              }}
                            >
                              {org.readings_count.toLocaleString()} readings
                            </span>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(255,255,255,0.06)",
                                color: "var(--clr-text-secondary)",
                              }}
                            >
                              {org.anomalies_count} anomalies
                            </span>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(255,255,255,0.06)",
                                color: "var(--clr-text-secondary)",
                              }}
                            >
                              {org.recommendations_count} recs
                            </span>
                            <span
                              style={{
                                fontSize: "11px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "rgba(255,255,255,0.06)",
                                color: "var(--clr-text-secondary)",
                              }}
                            >
                              {org.blocks_count} blks / {org.devices_count} devs
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
