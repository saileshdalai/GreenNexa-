"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { SuperAdminOverviewData, OrganisationOverviewItem } from "@/types";
import {
  Building2,
  Users,
  Cpu,
  AlertTriangle,
  Bell,
  CheckCircle2,
  PlusCircle,
  ExternalLink,
  Sliders,
  UserCheck,
  Power,
  Search,
  Filter,
  RefreshCw,
  Eye,
  Edit3,
  MapPin,
  LayoutDashboard,
  ChevronDown,
} from "lucide-react";
import { OrganisationEditModal } from "@/components/super-admin/OrganisationEditModal";
import { OrganisationViewModal } from "@/components/super-admin/OrganisationViewModal";
import { AddGovernmentOrgModal } from "@/components/municipality/AddGovernmentOrgModal";
import { isMunicipality } from "@/lib/organisation";

export default function SuperAdminOverviewPage() {
  const { user, setActiveOrgId } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [data, setData] = useState<SuperAdminOverviewData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [filterType, setFilterType] = useState<string>("ALL");
  const [editingOrgId, setEditingOrgId] = useState<string | null>(null);
  const [viewingOrgId, setViewingOrgId] = useState<string | null>(null);
  const [addMenuOrgId, setAddMenuOrgId] = useState<string | null>(null);
  const [associatingOrg, setAssociatingOrg] = useState<OrganisationOverviewItem | null>(null);

  const loadOverview = async () => {
    setLoading(true);
    try {
      const res = await api.get<SuperAdminOverviewData>("/api/v1/super-admin/overview");
      setData(res);
    } catch (err: any) {
      showToast(err.message || "Failed to load platform overview data", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadOverview();
  }, [user]);

  const handleViewDashboard = (orgId: string, orgName: string) => {
    setActiveOrgId(orgId);
    showToast(`Opening operational dashboard for ${orgName}`, "info");
    router.push(`/dashboard?org=${orgId}`);
  };

  const handleToggleOrgStatus = async (orgId: string, currentStatus: string) => {
    try {
      const isDeactivating = currentStatus === "Active";
      if (isDeactivating) {
        await api.delete(`/api/v1/organisations/${orgId}`);
        showToast(`Organisation ${orgId} deactivated successfully`, "success");
      } else {
        await api.put(`/api/v1/organisations/${orgId}`, { is_active: true });
        showToast(`Organisation ${orgId} activated successfully`, "success");
      }
      loadOverview();
    } catch (err: any) {
      showToast(err.message || "Failed to update organisation status", "error");
    }
  };

  const filteredOrgs = (data?.organisations || []).filter((org) => {
    const matchesSearch =
      org.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      org.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      org.facility_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      org.admin_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      org.location.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesFilter =
      filterType === "ALL" ||
      (filterType === "ACTIVE" && org.status === "Active") ||
      (filterType === "INACTIVE" && org.status === "Inactive") ||
      org.facility_type.toLowerCase() === filterType.toLowerCase();

    return matchesSearch && matchesFilter;
  });

  return (
    <AppLayout>
      {/* Header Title Section */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "4px" }}>
            <span style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10b981", padding: "6px 12px", borderRadius: "8px", fontSize: "12px", fontWeight: 800 }}>
              SUPER ADMIN PLATFORM
            </span>
          </div>
          <h1 style={{ fontSize: "32px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
            Platform Overview
          </h1>
          <p style={{ fontSize: "15px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            Manage and monitor your GreenNexa ecosystem.
          </p>
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <button
            onClick={loadOverview}
            className="btn btn-outline btn-sm"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
            title="Refresh Data"
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>

          <Link
            href="/super-admin/create"
            className="btn btn-primary btn-md"
            style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, padding: "10px 20px" }}
          >
            <PlusCircle size={18} />
            <span>+ Create Organisation</span>
          </Link>
        </div>
      </div>

      {/* Top 6 KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        {[
          { label: "Total Organisations", value: data?.total_organisations ?? "—", icon: <Building2 color="#3b82f6" size={22} />, bg: "rgba(59, 130, 246, 0.1)" },
          { label: "Active Organisations", value: data?.active_organisations ?? "—", icon: <CheckCircle2 color="#10b981" size={22} />, bg: "rgba(16, 185, 129, 0.1)" },
          { label: "Total Admins", value: data?.total_admins ?? "—", icon: <Users color="#8b5cf6" size={22} />, bg: "rgba(139, 92, 246, 0.1)" },
          { label: "Active IoT Devices", value: data?.active_iot_devices ?? "—", icon: <Cpu color="#06b6d4" size={22} />, bg: "rgba(6, 182, 212, 0.1)" },
          { label: "Platform Alerts", value: data?.platform_alerts ?? "—", icon: <Bell color="#f59e0b" size={22} />, bg: "rgba(245, 158, 11, 0.1)" },
          { label: "Critical Alerts", value: data?.critical_alerts ?? "—", icon: <AlertTriangle color="#ef4444" size={22} />, bg: "rgba(239, 68, 68, 0.1)" },
        ].map((kpi) => (
          <div key={kpi.label} className="card" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "12px", borderLeft: `4px solid ${kpi.bg}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--clr-text-secondary)" }}>{kpi.label}</span>
              <div style={{ width: "38px", height: "38px", borderRadius: "10px", background: kpi.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {kpi.icon}
              </div>
            </div>
            <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", lineHeight: 1 }}>
              {loading ? "..." : kpi.value}
            </div>
          </div>
        ))}
      </div>

      {/* ORGANISATION OVERVIEW Section */}
      <div className="card" style={{ padding: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h2 style={{ fontSize: "20px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
              <Building2 size={20} color="var(--clr-primary)" />
              ORGANISATION OVERVIEW
            </h2>
            <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>
              Real-time platform directory of all registered facilities and active configurations.
            </p>
          </div>

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            {/* Search filter */}
            <div style={{ position: "relative", minWidth: "240px" }}>
              <Search size={16} color="var(--clr-text-muted)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
              <input
                type="text"
                className="form-input"
                placeholder="Search organisations..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: "36px", fontSize: "13px", height: "38px" }}
              />
            </div>

            {/* Filter by Type / Status */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Filter size={14} color="var(--clr-text-muted)" />
              <select
                className="form-input"
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                style={{ fontSize: "13px", height: "38px", padding: "4px 10px" }}
              >
                <option value="ALL">All Statuses & Types</option>
                <option value="ACTIVE">Active Only</option>
                <option value="INACTIVE">Inactive Only</option>
                <option value="School">School</option>
                <option value="College / University">College / University</option>
                <option value="Hospital">Hospital</option>
                <option value="Municipality / Municipal Campus">Municipality</option>
                <option value="Industrial Estate">Industrial Estate</option>
                <option value="Public Sector Facility">Public Sector</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid var(--clr-border)", textAlign: "left", color: "var(--clr-text-muted)", fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                <th style={{ padding: "12px 16px" }}>Organisation</th>
                <th style={{ padding: "12px 16px" }}>Facility Type</th>
                <th style={{ padding: "12px 16px" }}>Location</th>
                <th style={{ padding: "12px 16px" }}>Admin</th>
                <th style={{ padding: "12px 16px" }}>Enabled Modules</th>
                <th style={{ padding: "12px 16px" }}>IoT Devices</th>
                <th style={{ padding: "12px 16px" }}>Status</th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrgs.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
                    {loading ? "Loading organisations data..." : "No organisations found matching filter criteria."}
                  </td>
                </tr>
              ) : (
                filteredOrgs.map((org) => (
                  <tr key={org.id} style={{ borderBottom: "1px solid var(--clr-border-light)", transition: "background 0.15s ease" }} className="table-row-hover">
                    {/* Organisation Name & ID */}
                    <td style={{ padding: "14px 16px" }}>
                      <div style={{ fontWeight: 700, color: "var(--clr-text-primary)", fontSize: "14px" }}>{org.name}</div>
                      <div style={{ fontSize: "11px", color: "var(--clr-primary)", fontFamily: "monospace", fontWeight: 600 }}>{org.id}</div>
                    </td>

                    {/* Facility Type */}
                    <td style={{ padding: "14px 16px" }}>
                      <span style={{ background: "var(--clr-surface-2)", border: "1px solid var(--clr-border)", padding: "4px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: 600 }}>
                        {org.facility_type}
                      </span>
                    </td>

                    {/* Location */}
                    <td style={{ padding: "14px 16px", color: "var(--clr-text-secondary)" }}>
                      {org.location}
                    </td>

                    {/* Admin */}
                    <td style={{ padding: "14px 16px" }}>
                      <div style={{ fontWeight: 600, color: "var(--clr-text-primary)" }}>{org.admin_name}</div>
                      <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>{org.admin_email}</div>
                    </td>

                    {/* Enabled Modules */}
                    <td style={{ padding: "14px 16px" }}>
                      <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", maxWidth: "260px" }}>
                        {org.enabled_modules.map((m) => (
                          <span
                            key={m}
                            style={{
                              fontSize: "10px",
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: "4px",
                              textTransform: "capitalize",
                              backgroundColor:
                                m.includes("energy") ? "rgba(245, 158, 11, 0.15)" :
                                m.includes("water") ? "rgba(59, 130, 246, 0.15)" :
                                m.includes("waste") ? "rgba(16, 185, 129, 0.15)" :
                                m.includes("air") || m.includes("temp") ? "rgba(139, 92, 246, 0.15)" :
                                "var(--clr-surface-2)",
                              color:
                                m.includes("energy") ? "#d97706" :
                                m.includes("water") ? "#2563eb" :
                                m.includes("waste") ? "#059669" :
                                m.includes("air") || m.includes("temp") ? "#7c3aed" :
                                "var(--clr-text-secondary)",
                            }}
                          >
                            {m.replace("_", " ")}
                          </span>
                        ))}
                      </div>
                    </td>

                    {/* IoT Devices */}
                    <td style={{ padding: "14px 16px", fontWeight: 600 }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <Cpu size={14} color="var(--clr-text-muted)" />
                        {org.iot_devices_count} devices
                      </span>
                    </td>

                    {/* Status */}
                    <td style={{ padding: "14px 16px" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          fontSize: "12px",
                          fontWeight: 700,
                          padding: "4px 10px",
                          borderRadius: "9999px",
                          backgroundColor: org.status === "Active" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                          color: org.status === "Active" ? "#10b981" : "#ef4444",
                        }}
                      >
                        <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: org.status === "Active" ? "#10b981" : "#ef4444" }} />
                        {org.status}
                      </span>
                    </td>

                    {/* Actions */}
                    <td style={{ padding: "14px 16px", textAlign: "right" }}>
                      <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end", alignItems: "center", flexWrap: "wrap", position: "relative" }}>
                        {/* 1. Edit */}
                        <button
                          onClick={() => setEditingOrgId(org.id)}
                          className="btn btn-outline btn-sm"
                          style={{
                            padding: "5px 10px",
                            fontSize: "12px",
                            gap: "4px",
                            color: "var(--clr-primary)",
                            borderColor: "var(--clr-primary)",
                            fontWeight: 700,
                            display: "inline-flex",
                            alignItems: "center",
                            backgroundColor: "rgba(26, 122, 60, 0.06)",
                          }}
                          title="Edit Organisation & Configuration"
                          aria-label={`Edit ${org.name}`}
                          id={`btn-edit-${org.id}`}
                        >
                          <Edit3 size={13} />
                          <span>Edit</span>
                        </button>

                        {/* 2. View */}
                        <button
                          onClick={() => setViewingOrgId(org.id)}
                          className="btn btn-outline btn-sm"
                          style={{
                            padding: "5px 10px",
                            fontSize: "12px",
                            gap: "4px",
                            color: "var(--clr-text-secondary)",
                            borderColor: "var(--clr-border)",
                            fontWeight: 600,
                            display: "inline-flex",
                            alignItems: "center",
                            backgroundColor: "var(--clr-surface-2)",
                          }}
                          title="View Organisation Details"
                          aria-label={`View ${org.name}`}
                          id={`btn-view-${org.id}`}
                        >
                          <Eye size={13} />
                          <span>View</span>
                        </button>

                        {/* 3. Dashboard */}
                        <button
                          onClick={() => handleViewDashboard(org.id, org.name)}
                          className="btn btn-primary btn-sm"
                          style={{ padding: "5px 10px", fontSize: "12px", gap: "4px", display: "inline-flex", alignItems: "center" }}
                          title="View Operational Dashboard"
                          aria-label={`Dashboard ${org.name}`}
                          id={`btn-dashboard-${org.id}`}
                        >
                          <LayoutDashboard size={13} />
                          <span>Dashboard</span>
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

                        <Link
                          href={`/super-admin/sensors?org=${org.id}`}
                          className="btn btn-outline btn-sm"
                          style={{ padding: "5px 8px", fontSize: "12px" }}
                          title="Manage Sensors"
                        >
                          <Sliders size={13} />
                        </Link>

                        <Link
                          href={`/super-admin/users?org=${org.id}`}
                          className="btn btn-outline btn-sm"
                          style={{ padding: "5px 8px", fontSize: "12px" }}
                          title="Manage Admin"
                        >
                          <UserCheck size={13} />
                        </Link>

                        <button
                          onClick={() => handleToggleOrgStatus(org.id, org.status)}
                          className="btn btn-outline btn-sm"
                          style={{ padding: "5px 8px", color: org.status === "Active" ? "#ef4444" : "#10b981" }}
                          title={org.status === "Active" ? "Deactivate Organisation" : "Activate Organisation"}
                        >
                          <Power size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Organisation Configuration Modal */}
      <OrganisationEditModal
        organisationId={editingOrgId}
        isOpen={Boolean(editingOrgId)}
        onClose={() => setEditingOrgId(null)}
        onSuccess={loadOverview}
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
            loadOverview();
            showToast("Municipality associations updated.", "success");
          }}
        />
      )}
    </AppLayout>
  );
}
