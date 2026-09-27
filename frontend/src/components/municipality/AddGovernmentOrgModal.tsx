"use client";

import React, { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { GovernmentOrgItem } from "@/types";
import {
  X,
  Building2,
  Search,
  CheckCircle2,
  Plus,
  Loader2,
  MapPin,
  ShieldCheck,
  AlertCircle,
  Check,
} from "lucide-react";

interface AddGovernmentOrgModalProps {
  municipalityId: string;
  municipalityName: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function AddGovernmentOrgModal({
  municipalityId,
  municipalityName,
  isOpen,
  onClose,
  onSuccess,
}: AddGovernmentOrgModalProps) {
  const { showToast } = useToast();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [allGovOrgs, setAllGovOrgs] = useState<GovernmentOrgItem[]>([]);
  const [associatedIds, setAssociatedIds] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedOrg, setSelectedOrg] = useState<GovernmentOrgItem | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load Government organisations and existing associations when modal opens
  useEffect(() => {
    if (!isOpen || !municipalityId) return;

    setSelectedOrg(null);
    setSearchTerm("");
    setErrorMsg(null);

    const loadData = async () => {
      setLoading(true);
      try {
        // 1. Fetch existing government organisations
        let govList: GovernmentOrgItem[] = [];
        try {
          const resGov = await api.get<GovernmentOrgItem[]>("/api/v1/super-admin/organisations/government");
          govList = resGov || [];
        } catch {
          try {
            const resGov2 = await api.get<GovernmentOrgItem[]>("/api/v1/organisations/government");
            govList = resGov2 || [];
          } catch {
            govList = [];
          }
        }

        // Strict client-side guarantee: ownership_type must be GOVERNMENT
        // (Private organisations must never appear in initial list, search, or counts)
        const strictGovOnly = govList.filter(
          (o) => !o.ownership_type || o.ownership_type.toUpperCase() === "GOVERNMENT"
        );
        setAllGovOrgs(strictGovOnly);

        // 2. Fetch already associated organisation IDs
        let currentAssocIds = new Set<string>();
        try {
          const resAssoc = await api.get<{ associated_gov_org_ids: string[] }>(
            `/api/v1/super-admin/organisations/${municipalityId}/municipality-associations`
          );
          currentAssocIds = new Set(resAssoc?.associated_gov_org_ids || []);
        } catch {
          try {
            const resAssoc2 = await api.get<{ municipality_id: string; associated_government_orgs: any[] }>(
              `/api/v1/organisations/${municipalityId}/associated-government-orgs`
            );
            const ids = (resAssoc2?.associated_government_orgs || []).map((o: any) => o.id);
            currentAssocIds = new Set(ids);
          } catch {
            currentAssocIds = new Set();
          }
        }
        setAssociatedIds(currentAssocIds);
      } catch (err: any) {
        setErrorMsg(err.message || "Failed to load government organisations.");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [isOpen, municipalityId]);

  // Filter out already-associated orgs and the municipality itself
  const availableGovOrgs = useMemo(() => {
    return allGovOrgs.filter((org) => {
      // Exclude already associated
      if (associatedIds.has(org.id)) return false;
      // Exclude municipality itself
      if (org.id === municipalityId) return false;
      // Exclude private (redundant safety check)
      if (org.ownership_type && org.ownership_type.toUpperCase() !== "GOVERNMENT") return false;
      return true;
    });
  }, [allGovOrgs, associatedIds, municipalityId]);

  // Filter based on search query (matching real organisation name or ID)
  const filteredOrgs = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    if (!q) return availableGovOrgs;
    return availableGovOrgs.filter(
      (org) =>
        org.name.toLowerCase().includes(q) ||
        org.id.toLowerCase().includes(q) ||
        (org.org_type && org.org_type.toLowerCase().includes(q))
    );
  }, [availableGovOrgs, searchTerm]);

  const handleAddAssociation = async () => {
    if (!selectedOrg) {
      showToast("Please select an organisation to associate.", "error");
      return;
    }

    setSaving(true);
    setErrorMsg(null);
    try {
      // Try super-admin update first
      const updatedList = Array.from(new Set([...associatedIds, selectedOrg.id]));
      let success = false;

      try {
        await api.put(`/api/v1/super-admin/organisations/${municipalityId}/municipality-associations`, {
          associated_gov_org_ids: updatedList,
        });
        success = true;
      } catch {
        // Fallback to organisations endpoint
        await api.post(`/api/v1/organisations/${municipalityId}/associated-government-orgs`, {
          associated_org_id: selectedOrg.id,
        });
        success = true;
      }

      if (success) {
        showToast(
          `Organisation "${selectedOrg.name}" successfully associated with ${municipalityName || "Municipality"}.`,
          "success"
        );
        if (onSuccess) onSuccess();
        onClose();
      }
    } catch (err: any) {
      const msg = err.message || "Failed to associate organisation.";
      setErrorMsg(msg);
      showToast(msg, "error");
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

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
        if (e.target === e.currentTarget && !saving) onClose();
      }}
      aria-modal="true"
      role="dialog"
      aria-labelledby="add-gov-org-title"
    >
      <div
        style={{
          backgroundColor: "var(--clr-surface)",
          border: "1px solid var(--clr-border)",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "720px",
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
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                backgroundColor: "rgba(2, 132, 199, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Building2 size={22} color="#0284c7" />
            </div>
            <div>
              <h2
                id="add-gov-org-title"
                style={{ fontSize: "18px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}
              >
                Add Organisation to Municipality
              </h2>
              <p style={{ fontSize: "12px", color: "var(--clr-text-muted)", margin: "2px 0 0" }}>
                Associate existing Government organisations with <strong>{municipalityName}</strong>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={saving}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--clr-text-muted)",
              cursor: saving ? "not-allowed" : "pointer",
              padding: "4px",
              borderRadius: "6px",
            }}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Association Notice */}
        <div
          style={{
            padding: "10px 24px",
            backgroundColor: "rgba(2, 132, 199, 0.06)",
            borderBottom: "1px solid rgba(2, 132, 199, 0.15)",
            fontSize: "12px",
            color: "#0284c7",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <ShieldCheck size={16} />
          <span>
            <strong>Association Only:</strong> Only existing <strong>Government</strong> organisations can be linked.
            Private organisations are excluded.
          </span>
        </div>

        {/* Body Content */}
        <div style={{ padding: "20px 24px", overflowY: "auto", flex: 1, display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Working Search Input */}
          <div style={{ position: "relative" }}>
            <Search
              size={16}
              style={{
                position: "absolute",
                left: "14px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--clr-text-muted)",
              }}
            />
            <input
              type="text"
              className="input"
              placeholder="Search organisation name (e.g., Rama, College, Hospital)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                paddingLeft: "40px",
                width: "100%",
                fontSize: "14px",
              }}
              autoFocus
              id="search-gov-org-input"
            />
          </div>

          {/* Counts & Info Bar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", color: "var(--clr-text-muted)" }}>
            <span>
              Selectable Government Organisations: <strong>{filteredOrgs.length}</strong>
            </span>
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                style={{ background: "none", border: "none", color: "var(--clr-primary)", cursor: "pointer", fontSize: "12px", padding: 0 }}
              >
                Clear Search
              </button>
            )}
          </div>

          {errorMsg && (
            <div
              style={{
                padding: "10px 14px",
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "8px",
                color: "#ef4444",
                fontSize: "13px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <AlertCircle size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* List of Organisations */}
          <div
            style={{
              border: "1px solid var(--clr-border)",
              borderRadius: "10px",
              maxHeight: "260px",
              overflowY: "auto",
              backgroundColor: "var(--clr-surface-2)",
            }}
          >
            {loading ? (
              <div style={{ padding: "36px", textAlign: "center", color: "var(--clr-text-muted)" }}>
                <Loader2 size={24} className="animate-spin" style={{ margin: "0 auto 8px" }} />
                <p style={{ margin: 0, fontSize: "13px" }}>Loading Government organisations from database...</p>
              </div>
            ) : filteredOrgs.length === 0 ? (
              <div style={{ padding: "36px 20px", textAlign: "center", color: "var(--clr-text-muted)" }}>
                <Building2 size={28} style={{ margin: "0 auto 8px", opacity: 0.5 }} />
                <p style={{ margin: 0, fontSize: "14px", fontWeight: 600 }}>
                  {searchTerm ? `No government organisation matching "${searchTerm}"` : "No available government organisations to add"}
                </p>
                <p style={{ margin: "4px 0 0", fontSize: "12px" }}>
                  All eligible government organisations may already be associated or none match the search.
                </p>
              </div>
            ) : (
              filteredOrgs.map((org) => {
                const isSelected = selectedOrg?.id === org.id;
                return (
                  <div
                    key={org.id}
                    onClick={() => setSelectedOrg(org)}
                    id={`gov-org-item-${org.id}`}
                    style={{
                      padding: "12px 16px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      borderBottom: "1px solid var(--clr-border-light)",
                      cursor: "pointer",
                      backgroundColor: isSelected ? "rgba(2, 132, 199, 0.12)" : "transparent",
                      borderLeft: isSelected ? "4px solid #0284c7" : "4px solid transparent",
                      transition: "all 0.15s ease",
                    }}
                    className="table-row-hover"
                  >
                    <div>
                      {/* Real Organisation Name */}
                      <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--clr-text-primary)" }}>
                        {org.name}
                      </div>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "4px", flexWrap: "wrap" }}>
                        <span style={{ fontSize: "11px", color: "var(--clr-primary)", fontFamily: "monospace", fontWeight: 600 }}>
                          {org.id}
                        </span>
                        <span
                          style={{
                            fontSize: "11px",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backgroundColor: "var(--clr-surface)",
                            border: "1px solid var(--clr-border)",
                            color: "var(--clr-text-secondary)",
                          }}
                        >
                          {org.org_type || "Government Facility"}
                        </span>
                        {org.location && (
                          <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "inline-flex", alignItems: "center", gap: "2px" }}>
                            <MapPin size={11} /> {org.location}
                          </span>
                        )}
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "9999px",
                          backgroundColor: org.is_active ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                          color: org.is_active ? "#10b981" : "#ef4444",
                        }}
                      >
                        {org.is_active ? "Active" : "Inactive"}
                      </span>
                      <div
                        style={{
                          width: "20px",
                          height: "20px",
                          borderRadius: "50%",
                          border: isSelected ? "2px solid #0284c7" : "2px solid var(--clr-border)",
                          backgroundColor: isSelected ? "#0284c7" : "transparent",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#fff",
                        }}
                      >
                        {isSelected && <Check size={12} strokeWidth={3} />}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Selected Organisation Details Card */}
          {selectedOrg && (
            <div
              style={{
                padding: "16px",
                borderRadius: "10px",
                backgroundColor: "rgba(2, 132, 199, 0.08)",
                border: "1px solid rgba(2, 132, 199, 0.25)",
              }}
            >
              <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", color: "#0284c7", marginBottom: "6px" }}>
                Ready to Associate
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px" }}>
                <div>
                  <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "block" }}>Organisation Name</span>
                  <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--clr-text-primary)" }}>{selectedOrg.name}</span>
                </div>
                <div>
                  <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "block" }}>Organisation Type</span>
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--clr-text-primary)" }}>{selectedOrg.org_type || "Facility"}</span>
                </div>
                <div>
                  <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "block" }}>Location</span>
                  <span style={{ fontSize: "13px", color: "var(--clr-text-secondary)" }}>{selectedOrg.location || "N/A"}</span>
                </div>
                <div>
                  <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", display: "block" }}>Status</span>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: selectedOrg.is_active ? "#10b981" : "#ef4444" }}>
                    {selectedOrg.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            </div>
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
            backgroundColor: "var(--clr-surface-2)",
          }}
        >
          <div style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>
            {selectedOrg ? (
              <span>Selected: <strong>{selectedOrg.name}</strong></span>
            ) : (
              <span>Select an organisation to enable Add</span>
            )}
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={onClose}
              disabled={saving}
              className="btn btn-outline"
              style={{ padding: "8px 16px", fontSize: "13px" }}
            >
              Cancel
            </button>
            <button
              onClick={handleAddAssociation}
              disabled={!selectedOrg || saving}
              className="btn btn-primary"
              id="confirm-add-to-municipality-btn"
              style={{
                padding: "8px 20px",
                fontSize: "13px",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: !selectedOrg ? "var(--clr-border)" : "#0284c7",
                borderColor: !selectedOrg ? "var(--clr-border)" : "#0284c7",
                cursor: !selectedOrg || saving ? "not-allowed" : "pointer",
              }}
            >
              {saving ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  <span>Adding...</span>
                </>
              ) : (
                <>
                  <Plus size={15} />
                  <span>Add to Municipality</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
