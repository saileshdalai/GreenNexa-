"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { FullOrganisationConfigResponse } from "@/types";
import {
  X,
  Building2,
  UserCheck,
  MapPin,
  Shield,
  Layers,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Eye,
  ExternalLink,
} from "lucide-react";

interface OrganisationViewModalProps {
  organisationId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onViewDashboard?: (orgId: string, orgName: string) => void;
}

export function OrganisationViewModal({
  organisationId,
  isOpen,
  onClose,
  onViewDashboard,
}: OrganisationViewModalProps) {
  const [data, setData] = useState<FullOrganisationConfigResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !organisationId) return;

    setLoading(true);
    setError(null);

    const loadDetails = async () => {
      try {
        let res: any = null;
        try {
          res = await api.get<FullOrganisationConfigResponse>(
            `/api/v1/super-admin/organisations/${organisationId}`
          );
        } catch {
          res = await api.get<any>(`/api/v1/organisations/${organisationId}`);
        }
        setData(res);
      } catch (err: any) {
        setError(err.message || "Failed to load organisation details.");
      } finally {
        setLoading(false);
      }
    };

    loadDetails();
  }, [isOpen, organisationId]);

  if (!isOpen) return null;

  const isMunicipality = (data?.facility_type || "").toLowerCase().includes("municipality");
  const blockLabel = isMunicipality ? "Wards" : "Facility Blocks";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      aria-modal="true"
      role="dialog"
      aria-labelledby="view-org-title"
    >
      <div
        style={{
          backgroundColor: "var(--clr-surface)",
          border: "1px solid var(--clr-border)",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "760px",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.35)",
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
            backgroundColor: "var(--clr-surface-2)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "10px",
                backgroundColor: "rgba(26, 122, 60, 0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Building2 size={22} color="var(--clr-primary)" />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h2
                  id="view-org-title"
                  style={{ fontSize: "18px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}
                >
                  {data?.organisation_name || organisationId}
                </h2>
                {data?.ownership_type && (
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 800,
                      padding: "2px 8px",
                      borderRadius: "9999px",
                      backgroundColor: data.ownership_type === "GOVERNMENT" ? "rgba(2, 132, 199, 0.15)" : "rgba(100, 116, 139, 0.15)",
                      color: data.ownership_type === "GOVERNMENT" ? "#0284c7" : "#64748b",
                      border: data.ownership_type === "GOVERNMENT" ? "1px solid rgba(2, 132, 199, 0.3)" : "1px solid rgba(100, 116, 139, 0.3)",
                    }}
                  >
                    {data.ownership_type}
                  </span>
                )}
              </div>
              <p style={{ fontSize: "12px", color: "var(--clr-text-muted)", margin: "2px 0 0" }}>
                Organisation Details & Configuration Overview (Read-Only)
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--clr-text-muted)",
              cursor: "pointer",
              padding: "4px",
              borderRadius: "6px",
            }}
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: "24px", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "20px" }}>
          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
              <Loader2 size={28} className="animate-spin" style={{ margin: "0 auto 10px" }} />
              <p style={{ margin: 0, fontSize: "14px" }}>Loading organisation data...</p>
            </div>
          ) : error ? (
            <div style={{ padding: "20px", backgroundColor: "rgba(239, 68, 68, 0.1)", borderRadius: "8px", color: "#ef4444" }}>
              {error}
            </div>
          ) : data ? (
            <>
              {/* Top Overview Cards */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px" }}>
                <div style={{ padding: "12px 14px", borderRadius: "10px", backgroundColor: "var(--clr-surface-2)", border: "1px solid var(--clr-border)" }}>
                  <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                    Facility Type
                  </span>
                  <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--clr-text-primary)", marginTop: "2px", display: "block" }}>
                    {data.facility_type || "Standard Facility"}
                  </span>
                </div>

                <div style={{ padding: "12px 14px", borderRadius: "10px", backgroundColor: "var(--clr-surface-2)", border: "1px solid var(--clr-border)" }}>
                  <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                    Status
                  </span>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12px",
                      fontWeight: 700,
                      padding: "2px 8px",
                      borderRadius: "9999px",
                      marginTop: "4px",
                      backgroundColor: data.is_active ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                      color: data.is_active ? "#10b981" : "#ef4444",
                    }}
                  >
                    <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: data.is_active ? "#10b981" : "#ef4444" }} />
                    {data.is_active ? "Active" : "Inactive"}
                  </span>
                </div>

                <div style={{ padding: "12px 14px", borderRadius: "10px", backgroundColor: "var(--clr-surface-2)", border: "1px solid var(--clr-border)" }}>
                  <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "block", textTransform: "uppercase", fontWeight: 700 }}>
                    Org ID / Code
                  </span>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--clr-primary)", fontFamily: "monospace", marginTop: "2px", display: "block" }}>
                    {data.organisation_id} {data.org_code ? `(${data.org_code})` : ""}
                  </span>
                </div>
              </div>

              {/* Location & Admin Sections */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                {/* Location Box */}
                <div style={{ padding: "16px", borderRadius: "10px", border: "1px solid var(--clr-border)", backgroundColor: "var(--clr-surface-2)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 700, color: "var(--clr-primary)", marginBottom: "8px" }}>
                    <MapPin size={15} /> LOCATION & ADDRESS
                  </div>
                  <div style={{ fontSize: "13px", color: "var(--clr-text-primary)", fontWeight: 600 }}>
                    {data.facility_name || data.organisation_name}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
                    {data.address || "No street address specified"}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "2px" }}>
                    {[data.city, data.district, data.state].filter(Boolean).join(", ") || data.location}
                  </div>
                </div>

                {/* Admin Box */}
                <div style={{ padding: "16px", borderRadius: "10px", border: "1px solid var(--clr-border)", backgroundColor: "var(--clr-surface-2)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 700, color: "var(--clr-primary)", marginBottom: "8px" }}>
                    <UserCheck size={15} /> ADMINISTRATOR
                  </div>
                  <div style={{ fontSize: "13px", color: "var(--clr-text-primary)", fontWeight: 600 }}>
                    {data.admin_name || "Admin"}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
                    {data.admin_email || "No email"}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "2px", fontFamily: "monospace" }}>
                    User ID: {data.admin_user_id || "N/A"}
                  </div>
                </div>
              </div>

              {/* Blocks / Wards Section */}
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 700, color: "var(--clr-text-primary)", marginBottom: "10px" }}>
                  <Layers size={15} color="var(--clr-primary)" /> {blockLabel.toUpperCase()} ({data.blocks?.length || 0})
                </div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  {(data.blocks || []).length === 0 ? (
                    <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>No {blockLabel.toLowerCase()} configured</span>
                  ) : (
                    data.blocks.map((b: { block_id: string; block_name: string; is_active?: boolean }) => (
                      <span
                        key={b.block_id || b.block_name}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          padding: "6px 10px",
                          borderRadius: "8px",
                          backgroundColor: "var(--clr-surface-2)",
                          border: "1px solid var(--clr-border)",
                          fontSize: "12px",
                          fontWeight: 600,
                          color: "var(--clr-text-primary)",
                        }}
                      >
                        <span style={{ fontSize: "10px", color: "var(--clr-primary)", fontFamily: "monospace" }}>
                          {b.block_id}
                        </span>
                        {b.block_name}
                      </span>
                    ))
                  )}
                </div>
              </div>

              {/* Enabled Modules */}
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 700, color: "var(--clr-text-primary)", marginBottom: "10px" }}>
                  <Sliders size={15} color="var(--clr-primary)" /> OPERATIONAL MODULES ({data.enabled_modules?.length || 0})
                </div>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {(data.enabled_modules || []).map((m: string) => (
                    <span
                      key={m}
                      style={{
                        padding: "4px 10px",
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontWeight: 700,
                        textTransform: "capitalize",
                        backgroundColor: "rgba(26, 122, 60, 0.1)",
                        color: "var(--clr-primary)",
                        border: "1px solid rgba(26, 122, 60, 0.2)",
                      }}
                    >
                      {m.replace("_", " ")}
                    </span>
                  ))}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--clr-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: "10px",
            backgroundColor: "var(--clr-surface-2)",
          }}
        >
          <button onClick={onClose} className="btn btn-outline" style={{ padding: "8px 16px", fontSize: "13px" }}>
            Close
          </button>
          {data && onViewDashboard && (
            <button
              onClick={() => {
                onViewDashboard(data.organisation_id, data.organisation_name);
                onClose();
              }}
              className="btn btn-primary"
              style={{ padding: "8px 18px", fontSize: "13px", display: "inline-flex", alignItems: "center", gap: "6px" }}
            >
              <Eye size={14} />
              <span>Go to Dashboard</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
