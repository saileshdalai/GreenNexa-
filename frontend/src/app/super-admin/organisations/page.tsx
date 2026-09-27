"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { OrganisationOverviewItem } from "@/types";
import {
  Building2,
  PlusCircle,
  Eye,
  Sliders,
  UserCheck,
  Search,
  RefreshCw,
  MapPin,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  X,
  ShieldAlert,
  Edit3,
  LayoutDashboard,
  ChevronDown,
} from "lucide-react";
import { OrganisationEditModal } from "@/components/super-admin/OrganisationEditModal";
import { OrganisationViewModal } from "@/components/super-admin/OrganisationViewModal";
import { AddGovernmentOrgModal } from "@/components/municipality/AddGovernmentOrgModal";
import { isMunicipality } from "@/lib/organisation";

export default function OrganisationsManagementPage() {
  const { user, setActiveOrgId } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [orgs, setOrgs] = useState<OrganisationOverviewItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusTab, setStatusTab] = useState<"ACTIVE" | "INACTIVE" | "ALL">("ACTIVE");

  // Confirmation & Edit Modals State
  const [deactivateTarget, setDeactivateTarget] = useState<OrganisationOverviewItem | null>(null);
  const [reactivateTarget, setReactivateTarget] = useState<OrganisationOverviewItem | null>(null);
  const [editingOrgId, setEditingOrgId] = useState<string | null>(null);
  const [viewingOrgId, setViewingOrgId] = useState<string | null>(null);
  const [addMenuOrgId, setAddMenuOrgId] = useState<string | null>(null);
  const [associatingOrg, setAssociatingOrg] = useState<OrganisationOverviewItem | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const loadOrgs = async () => {
    setLoading(true);
    try {
      let rawOrgs: any[] = [];
      try {
        const overviewRes = await api.get<any>("/api/v1/super-admin/overview");
        if (overviewRes && Array.isArray(overviewRes.organisations)) {
          rawOrgs = overviewRes.organisations;
        }
      } catch {
        // Fallback to /api/v1/organisations endpoint
      }

      if (rawOrgs.length === 0) {
        const orgListRes = await api.get<any>("/api/v1/organisations");
        const items = Array.isArray(orgListRes) ? orgListRes : orgListRes?.items || [];
        rawOrgs = items.map((o: any) => ({
          id: o.id,
          name: o.name,
          facility_type: o.facility_type || o.org_type || "Facility",
          location: o.location || [o.city, o.state].filter(Boolean).join(", ") || "Location Not Set",
          admin_name: o.admin_name || (o.name + " Admin"),
          admin_email: o.admin_email || o.contact_email || "N/A",
          enabled_modules: o.enabled_modules || ["energy", "water", "temperature", "humidity"],
          iot_devices_count: o.iot_devices_count || 0,
          status: o.status || (o.is_active !== false ? "Active" : "Inactive"),
          created_at: o.created_at || new Date().toISOString(),
        }));
      }

      setOrgs(rawOrgs);
    } catch (err: any) {
      showToast(err.message || "Failed to load organisations", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadOrgs();
  }, [user]);

  const handleViewDashboard = (orgId: string, orgName: string) => {
    setActiveOrgId(orgId);
    showToast(`Opening operational dashboard for ${orgName}`, "info");
    router.push(`/dashboard?org=${orgId}`);
  };

  const handleConfirmDeactivate = async () => {
    if (!deactivateTarget) return;
    setActionLoading(true);
    try {
      await api.delete(`/api/v1/organisations/${deactivateTarget.id}`);
      showToast(`Organisation ${deactivateTarget.name} (${deactivateTarget.id}) successfully deactivated.`, "success");
      setDeactivateTarget(null);
      await loadOrgs();
    } catch (err: any) {
      showToast(err.message || "Failed to deactivate organisation", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmReactivate = async () => {
    if (!reactivateTarget) return;
    setActionLoading(true);
    try {
      await api.post(`/api/v1/organisations/${reactivateTarget.id}/reactivate`);
      showToast(`Organisation ${reactivateTarget.name} (${reactivateTarget.id}) reactivated. Admin access restored.`, "success");
      setReactivateTarget(null);
      await loadOrgs();
    } catch (err: any) {
      showToast(err.message || "Failed to reactivate organisation", "error");
    } finally {
      setActionLoading(false);
    }
  };

  const activeCount = orgs.filter((o) => o.status === "Active").length;
  const inactiveCount = orgs.filter((o) => o.status !== "Active").length;

  const filtered = orgs
    .filter((o) => {
      if (statusTab === "ACTIVE") return o.status === "Active";
      if (statusTab === "INACTIVE") return o.status !== "Active";
      return true;
    })
    .filter(
      (o) =>
        o.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        o.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        o.facility_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        o.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
        o.admin_email.toLowerCase().includes(searchTerm.toLowerCase())
    );

  return (
    <AppLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
            <Building2 color="var(--clr-primary)" size={28} />
            Organisations Management
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            Comprehensive directory and operational controls for all tenant facilities.
          </p>
        </div>

        <div style={{ display: "flex", gap: "12px" }}>
          <button onClick={loadOrgs} className="btn btn-outline btn-sm" title="Refresh list">
            <RefreshCw size={14} className={loading ? "spin" : ""} />
          </button>
          <Link href="/super-admin/create" className="btn btn-primary btn-md" style={{ gap: "8px", fontWeight: 700 }}>
            <PlusCircle size={18} />
            <span>+ Create Organisation</span>
          </Link>
        </div>
      </div>

      {/* Status Filter Tabs & Search Bar */}
      <div className="card" style={{ padding: "16px 20px", marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          {/* Filter Tabs */}
          <div style={{ display: "flex", gap: "8px", background: "var(--clr-surface-2)", padding: "4px", borderRadius: "8px" }}>
            <button
              onClick={() => setStatusTab("ACTIVE")}
              style={{
                border: "none",
                background: statusTab === "ACTIVE" ? "var(--clr-primary)" : "transparent",
                color: statusTab === "ACTIVE" ? "#ffffff" : "var(--clr-text-secondary)",
                padding: "6px 14px",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.15s ease",
              }}
            >
              <span>Active</span>
              <span style={{ fontSize: "11px", background: statusTab === "ACTIVE" ? "rgba(255,255,255,0.25)" : "rgba(100,116,139,0.2)", padding: "1px 6px", borderRadius: "10px" }}>
                {activeCount}
              </span>
            </button>

            <button
              onClick={() => setStatusTab("INACTIVE")}
              style={{
                border: "none",
                background: statusTab === "INACTIVE" ? "var(--clr-primary)" : "transparent",
                color: statusTab === "INACTIVE" ? "#ffffff" : "var(--clr-text-secondary)",
                padding: "6px 14px",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.15s ease",
              }}
            >
              <span>Inactive</span>
              <span style={{ fontSize: "11px", background: statusTab === "INACTIVE" ? "rgba(255,255,255,0.25)" : "rgba(100,116,139,0.2)", padding: "1px 6px", borderRadius: "10px" }}>
                {inactiveCount}
              </span>
            </button>

            <button
              onClick={() => setStatusTab("ALL")}
              style={{
                border: "none",
                background: statusTab === "ALL" ? "var(--clr-primary)" : "transparent",
                color: statusTab === "ALL" ? "#ffffff" : "var(--clr-text-secondary)",
                padding: "6px 14px",
                borderRadius: "6px",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                transition: "all 0.15s ease",
              }}
            >
              <span>All</span>
              <span style={{ fontSize: "11px", background: statusTab === "ALL" ? "rgba(255,255,255,0.25)" : "rgba(100,116,139,0.2)", padding: "1px 6px", borderRadius: "10px" }}>
                {orgs.length}
              </span>
            </button>
          </div>

          {/* Search Input */}
          <div style={{ position: "relative", minWidth: "280px", flex: 1, maxWidth: "420px" }}>
            <Search size={16} color="var(--clr-text-muted)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
            <input
              type="text"
              className="form-input"
              placeholder="Search by name, ID, location, or admin..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ paddingLeft: "36px", width: "100%" }}
            />
          </div>
        </div>
      </div>

      {/* Organisations Table */}
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ background: "var(--clr-surface-2)", borderBottom: "2px solid var(--clr-border)", textAlign: "left", color: "var(--clr-text-muted)", fontSize: "12px", fontWeight: 700, textTransform: "uppercase" }}>
                <th style={{ padding: "14px 20px" }}>Organisation ID & Name</th>
                <th style={{ padding: "14px 20px" }}>Facility Type</th>
                <th style={{ padding: "14px 20px" }}>Location</th>
                <th style={{ padding: "14px 20px" }}>Admin Contact</th>
                <th style={{ padding: "14px 20px" }}>Enabled Modules</th>
                <th style={{ padding: "14px 20px" }}>Status</th>
                <th style={{ padding: "14px 20px", textAlign: "right", minWidth: "260px" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
                    {loading ? "Loading organisations..." : `No ${statusTab.toLowerCase()} organisations found matching filter.`}
                  </td>
                </tr>
              ) : (
                filtered.map((org) => {
                  const isActive = org.status === "Active";
                  return (
                    <tr key={org.id} style={{ borderBottom: "1px solid var(--clr-border-light)", opacity: isActive ? 1 : 0.75 }} className="table-row-hover">
                      <td style={{ padding: "16px 20px" }}>
                        <div style={{ fontWeight: 800, fontSize: "15px", color: "var(--clr-text-primary)" }}>{org.name}</div>
                        <div style={{ fontSize: "11px", color: "var(--clr-primary)", fontFamily: "monospace", fontWeight: 700 }}>{org.id}</div>
                      </td>

                      <td style={{ padding: "16px 20px" }}>
                        <span style={{ background: "var(--clr-surface-2)", border: "1px solid var(--clr-border)", padding: "4px 10px", borderRadius: "6px", fontWeight: 600 }}>
                          {org.facility_type}
                        </span>
                      </td>

                      <td style={{ padding: "16px 20px", color: "var(--clr-text-secondary)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <MapPin size={14} color="var(--clr-text-muted)" />
                          {org.location}
                        </div>
                      </td>

                      <td style={{ padding: "16px 20px" }}>
                        <div style={{ fontWeight: 600 }}>{org.admin_name}</div>
                        <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>{org.admin_email}</div>
                      </td>

                      <td style={{ padding: "16px 20px" }}>
                        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", maxWidth: "240px" }}>
                          {org.enabled_modules.map((m) => (
                            <span key={m} style={{ fontSize: "10px", fontWeight: 700, padding: "2px 6px", borderRadius: "4px", background: "var(--clr-primary-light)", color: "var(--clr-primary)", textTransform: "capitalize" }}>
                              {m.replace("_", " ")}
                            </span>
                          ))}
                        </div>
                      </td>

                      <td style={{ padding: "16px 20px" }}>
                        <span
                          style={{
                            fontSize: "12px",
                            fontWeight: 700,
                            padding: "4px 10px",
                            borderRadius: "9999px",
                            background: isActive ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                            color: isActive ? "#10b981" : "#ef4444",
                            border: isActive ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(239, 68, 68, 0.3)",
                          }}
                        >
                          {org.status}
                        </span>
                      </td>

                      <td style={{ padding: "16px 20px", textAlign: "right", minWidth: "260px" }}>
                        <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end", alignItems: "center", flexWrap: "wrap", position: "relative" }}>
                          {/* 1. Edit */}
                          <button
                            onClick={() => setEditingOrgId(org.id)}
                            className="btn btn-outline btn-sm"
                            style={{
                              gap: "4px",
                              fontSize: "12px",
                              fontWeight: 700,
                              color: "var(--clr-primary)",
                              borderColor: "var(--clr-primary)",
                              backgroundColor: "rgba(26, 122, 60, 0.06)",
                              display: "inline-flex",
                              alignItems: "center",
                            }}
                            title="Edit Organisation & Configuration"
                            aria-label={`Edit ${org.name}`}
                            id={`btn-edit-${org.id}`}
                          >
                            <Edit3 size={13} /> <span>Edit</span>
                          </button>

                          {/* 2. View */}
                          <button
                            onClick={() => setViewingOrgId(org.id)}
                            className="btn btn-outline btn-sm"
                            style={{
                              gap: "4px",
                              fontSize: "12px",
                              fontWeight: 600,
                              color: "var(--clr-text-secondary)",
                              borderColor: "var(--clr-border)",
                              backgroundColor: "var(--clr-surface-2)",
                              display: "inline-flex",
                              alignItems: "center",
                            }}
                            title="View Organisation Details"
                            aria-label={`View ${org.name}`}
                            id={`btn-view-${org.id}`}
                          >
                            <Eye size={13} /> <span>View</span>
                          </button>

                          {/* 3. Dashboard */}
                          <button
                            onClick={() => handleViewDashboard(org.id, org.name)}
                            className="btn btn-primary btn-sm"
                            style={{ gap: "4px", fontSize: "12px", display: "inline-flex", alignItems: "center" }}
                            title="View Facility Operational Dashboard"
                            aria-label={`Dashboard ${org.name}`}
                            id={`btn-dashboard-${org.id}`}
                          >
                            <LayoutDashboard size={13} /> <span>Dashboard</span>
                          </button>

                          {/* 4. Add action: ONLY for Municipality organisations */}
                          {isMunicipality(org) && (
                            <div style={{ position: "relative", display: "inline-block" }}>
                              <button
                                onClick={() => setAddMenuOrgId(addMenuOrgId === org.id ? null : org.id)}
                                className="btn btn-sm"
                                style={{
                                  padding: "5px 10px",
                                  fontSize: "12px",
                                  gap: "4px",
                                  color: "#0284c7",
                                  borderColor: "#0284c7",
                                  fontWeight: 700,
                                  display: "inline-flex",
                                  alignItems: "center",
                                  backgroundColor: "rgba(2, 132, 199, 0.1)",
                                  border: "1px solid #0284c7",
                                }}
                                title="Add Ward or Organisation"
                                aria-label={`Add to municipality ${org.name}`}
                                id={`btn-add-municipality-${org.id}`}
                              >
                                <PlusCircle size={13} />
                                <span>Add</span>
                                <ChevronDown size={11} />
                              </button>

                              {/* Dropdown Menu: Ward + Organisation */}
                              {addMenuOrgId === org.id && (
                                <div
                                  style={{
                                    position: "absolute",
                                    right: 0,
                                    top: "100%",
                                    marginTop: "4px",
                                    width: "160px",
                                    backgroundColor: "var(--clr-surface)",
                                    border: "1px solid var(--clr-border)",
                                    borderRadius: "8px",
                                    boxShadow: "0 10px 25px -5px rgba(0,0,0,0.25)",
                                    zIndex: 50,
                                    overflow: "hidden",
                                    textAlign: "left",
                                  }}
                                >
                                  <Link
                                    href={`/super-admin/organisations/${org.id}/municipality?tab=wards`}
                                    onClick={() => setAddMenuOrgId(null)}
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "8px",
                                      padding: "8px 12px",
                                      fontSize: "12px",
                                      fontWeight: 600,
                                      color: "var(--clr-text-primary)",
                                      textDecoration: "none",
                                      borderBottom: "1px solid var(--clr-border-light)",
                                      transition: "background 0.15s ease",
                                    }}
                                    className="table-row-hover"
                                    id={`menu-add-ward-${org.id}`}
                                  >
                                    <MapPin size={13} color="#0284c7" />
                                    <span>Ward</span>
                                  </Link>
                                  <button
                                    onClick={() => {
                                      setAddMenuOrgId(null);
                                      setAssociatingOrg(org);
                                    }}
                                    style={{
                                      width: "100%",
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "8px",
                                      padding: "8px 12px",
                                      fontSize: "12px",
                                      fontWeight: 600,
                                      color: "var(--clr-text-primary)",
                                      background: "none",
                                      border: "none",
                                      cursor: "pointer",
                                      textAlign: "left",
                                      transition: "background 0.15s ease",
                                    }}
                                    className="table-row-hover"
                                    id={`menu-add-org-${org.id}`}
                                  >
                                    <Building2 size={13} color="var(--clr-primary)" />
                                    <span>Organisation</span>
                                  </button>
                                </div>
                              )}
                            </div>
                          )}

                          <Link href={`/super-admin/sensors?org=${org.id}`} className="btn btn-outline btn-sm" title="Configure Sensor Baselines & Thresholds">
                            <Sliders size={13} />
                          </Link>
                          <Link href={`/super-admin/users?org=${org.id}`} className="btn btn-outline btn-sm" title="Manage Administrators">
                            <UserCheck size={13} />
                          </Link>
                          {isActive ? (
                            <button
                              onClick={() => setDeactivateTarget(org)}
                              className="btn btn-outline btn-sm"
                              style={{ color: "#ef4444", borderColor: "rgba(239, 68, 68, 0.3)" }}
                              title="Delete / Deactivate Organisation"
                            >
                              <Trash2 size={13} />
                            </button>
                          ) : (
                            <button
                              onClick={() => setReactivateTarget(org)}
                              className="btn btn-outline btn-sm"
                              style={{ color: "#10b981", borderColor: "rgba(16, 185, 129, 0.3)" }}
                              title="Reactivate Organisation"
                            >
                              <RefreshCw size={13} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Deactivation Confirmation Modal */}
      {deactivateTarget && (
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
            padding: "20px",
          }}
        >
          <div
            style={{
              backgroundColor: "var(--clr-surface-1, #1e293b)",
              borderRadius: "14px",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              maxWidth: "480px",
              width: "100%",
              padding: "24px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#ef4444" }}>
                <AlertTriangle size={24} />
                <h2 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "var(--clr-text-primary)" }}>
                  Deactivate Organisation?
                </h2>
              </div>
              <button
                onClick={() => setDeactivateTarget(null)}
                style={{ background: "transparent", border: "none", color: "var(--clr-text-muted)", cursor: "pointer" }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ marginBottom: "20px", fontSize: "14px", color: "var(--clr-text-secondary)", lineHeight: 1.6 }}>
              <p style={{ margin: "0 0 12px 0" }}>
                You are about to deactivate:
              </p>
              <div style={{ background: "var(--clr-surface-2)", padding: "12px 14px", borderRadius: "8px", border: "1px solid var(--clr-border)", marginBottom: "16px" }}>
                <div style={{ fontWeight: 800, color: "var(--clr-text-primary)", fontSize: "15px" }}>{deactivateTarget.name}</div>
                <div style={{ fontSize: "12px", color: "var(--clr-primary)", fontFamily: "monospace", marginTop: "2px" }}>ID: {deactivateTarget.id}</div>
                <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
                  Facility Type: {deactivateTarget.facility_type} | Admin: {deactivateTarget.admin_email}
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px", padding: "12px", borderRadius: "8px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.25)", color: "#fca5a5", fontSize: "13px" }}>
                <ShieldAlert size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
                <div>
                  <strong>Consequences:</strong>
                  <ul style={{ margin: "4px 0 0 0", paddingLeft: "16px" }}>
                    <li>Organisation status becomes <strong>Inactive</strong>.</li>
                    <li>Administrator login and dashboard access will be <strong>blocked</strong>.</li>
                    <li>All historical sensor readings, telemetry, and anomaly records <strong>remain safely preserved</strong>.</li>
                  </ul>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
              <button
                type="button"
                onClick={() => setDeactivateTarget(null)}
                disabled={actionLoading}
                className="btn btn-outline btn-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDeactivate}
                disabled={actionLoading}
                className="btn btn-md"
                style={{ backgroundColor: "#ef4444", color: "#ffffff", borderColor: "#ef4444", fontWeight: 700 }}
              >
                {actionLoading ? "Deactivating..." : "Deactivate Organisation"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reactivation Confirmation Modal */}
      {reactivateTarget && (
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
            padding: "20px",
          }}
        >
          <div
            style={{
              backgroundColor: "var(--clr-surface-1, #1e293b)",
              borderRadius: "14px",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              maxWidth: "480px",
              width: "100%",
              padding: "24px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#10b981" }}>
                <CheckCircle2 size={24} />
                <h2 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "var(--clr-text-primary)" }}>
                  Reactivate Organisation?
                </h2>
              </div>
              <button
                onClick={() => setReactivateTarget(null)}
                style={{ background: "transparent", border: "none", color: "var(--clr-text-muted)", cursor: "pointer" }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ marginBottom: "20px", fontSize: "14px", color: "var(--clr-text-secondary)", lineHeight: 1.6 }}>
              <p style={{ margin: "0 0 12px 0" }}>
                Reactivate the following organisation and restore its administrator accounts:
              </p>
              <div style={{ background: "var(--clr-surface-2)", padding: "12px 14px", borderRadius: "8px", border: "1px solid var(--clr-border)", marginBottom: "16px" }}>
                <div style={{ fontWeight: 800, color: "var(--clr-text-primary)", fontSize: "15px" }}>{reactivateTarget.name}</div>
                <div style={{ fontSize: "12px", color: "var(--clr-primary)", fontFamily: "monospace", marginTop: "2px" }}>ID: {reactivateTarget.id}</div>
                <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "4px" }}>
                  Facility Type: {reactivateTarget.facility_type} | Admin: {reactivateTarget.admin_email}
                </div>
              </div>

              <p style={{ margin: 0, fontSize: "13px", color: "#34d399" }}>
                ✓ Admin login will be re-enabled and the organisation will return to the active directory.
              </p>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
              <button
                type="button"
                onClick={() => setReactivateTarget(null)}
                disabled={actionLoading}
                className="btn btn-outline btn-md"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmReactivate}
                disabled={actionLoading}
                className="btn btn-md"
                style={{ backgroundColor: "#10b981", color: "#ffffff", borderColor: "#10b981", fontWeight: 700 }}
              >
                {actionLoading ? "Reactivating..." : "Reactivate Organisation"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Organisation Full Configuration Modal */}
      <OrganisationEditModal
        organisationId={editingOrgId}
        isOpen={Boolean(editingOrgId)}
        onClose={() => setEditingOrgId(null)}
        onSuccess={loadOrgs}
      />

      {/* View Organisation Details Modal */}
      <OrganisationViewModal
        organisationId={viewingOrgId}
        isOpen={Boolean(viewingOrgId)}
        onClose={() => setViewingOrgId(null)}
        onViewDashboard={handleViewDashboard}
      />

      {/* Add Government Organisation to Municipality Modal */}
      {associatingOrg && (
        <AddGovernmentOrgModal
          municipalityId={associatingOrg.id}
          municipalityName={associatingOrg.name}
          isOpen={Boolean(associatingOrg)}
          onClose={() => setAssociatingOrg(null)}
          onSuccess={() => {
            loadOrgs();
            showToast("Municipality associations updated.", "success");
          }}
        />
      )}
    </AppLayout>
  );
}

