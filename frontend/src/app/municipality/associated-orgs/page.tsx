"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { AssociatedGovOrg } from "@/types";
import { Building2, RefreshCw, ExternalLink, CheckCircle2, XCircle, Plus, ArrowLeft } from "lucide-react";
import { AddGovernmentOrgModal } from "@/components/municipality/AddGovernmentOrgModal";
import { MunicipalityOrgOverview } from "@/components/municipality/MunicipalityOrgOverview";

function AssociatedOrgsContent() {
  const { user, activeOrgId } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [orgs, setOrgs] = useState<AssociatedGovOrg[]>([]);
  const [loading, setLoading] = useState(true);
  const [municipalityName, setMunicipalityName] = useState("");
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedOrgForView, setSelectedOrgForView] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    if (searchParams.get("action") === "add") {
      setIsAddModalOpen(true);
    }
    const viewId = searchParams.get("view");
    if (viewId) {
      const match = orgs.find((o) => o.id === viewId);
      setSelectedOrgForView({ id: viewId, name: match ? match.name : viewId });
    }
  }, [searchParams, orgs]);

  useEffect(() => {
    if (!user) return;

    // Only Municipality Admins or Super Admins can access this page
    if (user.role !== "ADMIN" && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }

    const queryOrg = searchParams.get("org");
    const orgId = (user.role === "SUPER_ADMIN" ? (queryOrg || activeOrgId || user.organisation_id) : user.organisation_id) || "";
    if (!orgId) {
      router.push("/dashboard");
      return;
    }

    loadAssociatedOrgs(orgId);
  }, [user, searchParams, activeOrgId]);

  const queryOrg = searchParams.get("org");
  const effectiveOrgId = (user?.role === "SUPER_ADMIN" ? (queryOrg || activeOrgId || user?.organisation_id) : user?.organisation_id) || "";
  const backHref = effectiveOrgId ? `/dashboard?org=${encodeURIComponent(effectiveOrgId)}` : "/dashboard";

  const loadAssociatedOrgs = async (orgId: string) => {
    setLoading(true);
    try {
      // Fetch municipality name
      try {
        const orgData = await api.get<any>(`/api/v1/organisations/${orgId}`);
        setMunicipalityName(orgData?.name || orgId);

        // Check if it's actually a municipality
        if (orgData?.org_type && !(orgData.org_type as string).toLowerCase().includes("municipality")) {
          // Not a municipality, redirect
          if (user?.role !== "SUPER_ADMIN") {
            router.push("/dashboard");
            return;
          }
        }
      } catch {
        setMunicipalityName(orgId);
      }

      const res = await api.get<{ municipality_id: string; associated_government_orgs: AssociatedGovOrg[] }>(
        `/api/v1/organisations/${orgId}/associated-government-orgs`
      );
      setOrgs(res?.associated_government_orgs || []);
    } catch (err: any) {
      if (err?.status === 403) {
        showToast("This page is only accessible to Municipality administrators.", "error");
        router.push("/dashboard");
      } else {
        showToast(err?.message || "Failed to load associated organisations.", "error");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <Link
          href={backHref}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "13px",
            color: "var(--clr-primary)",
            fontWeight: 600,
            textDecoration: "none",
            marginBottom: "12px",
          }}
        >
          <ArrowLeft size={16} /> Back to Municipality Dashboard
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
          <div style={{ width: "36px", height: "36px", borderRadius: "10px", background: "rgba(2, 132, 199, 0.15)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Building2 size={18} color="#0284c7" />
          </div>
          <div>
            <h1 style={{ fontSize: "22px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
              Associated Government Organisations
            </h1>
            <p style={{ fontSize: "13px", color: "var(--clr-text-muted)", margin: "2px 0 0" }}>
              {municipalityName || "Municipality"} — read-only view of linked government organisations
            </p>
          </div>
        </div>

        <div style={{ padding: "10px 14px", background: "rgba(2, 132, 199, 0.06)", border: "1px solid rgba(2, 132, 199, 0.2)", borderRadius: "8px", fontSize: "13px", color: "#0284c7", marginTop: "12px" }}>
          <strong>Read-only view.</strong> These organisations are associated with your municipality for monitoring purposes. You cannot modify their data.
        </div>
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="btn btn-primary btn-sm"
          style={{ display: "inline-flex", alignItems: "center", gap: "6px", backgroundColor: "#0284c7", borderColor: "#0284c7" }}
          id="btn-open-add-org-modal"
        >
          <Plus size={14} />
          <span>Add Organisation</span>
        </button>

        <button
          onClick={() => effectiveOrgId && loadAssociatedOrgs(effectiveOrgId)}
          className="btn btn-outline btn-sm"
          style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? "spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px", color: "var(--clr-text-muted)" }}>
          <RefreshCw size={28} className="spin" style={{ marginBottom: "12px", opacity: 0.4 }} />
          <p>Loading associated organisations...</p>
        </div>
      ) : orgs.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px", color: "var(--clr-text-muted)" }}>
          <Building2 size={36} style={{ marginBottom: "12px", opacity: 0.3 }} />
          <p style={{ fontWeight: 600, fontSize: "16px" }}>No associated organisations</p>
          <p style={{ fontSize: "13px", marginTop: "6px" }}>
            A Super Admin must associate Government organisations with this municipality first.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {orgs.map((org) => (
            <div
              key={org.id}
              onClick={() => setSelectedOrgForView({ id: org.id, name: org.name })}
              style={{
                background: "var(--clr-surface-1)",
                border: "1px solid var(--clr-border)",
                borderRadius: "12px",
                padding: "18px 20px",
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "16px",
                flexWrap: "wrap",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
              className="hover:border-primary"
            >
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                  <span style={{ fontWeight: 800, fontSize: "16px", color: "var(--clr-text-primary)" }}>{org.name}</span>
                  {org.is_active ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "11px", fontWeight: 700, color: "#10b981", background: "rgba(16,185,129,0.1)", padding: "2px 8px", borderRadius: "20px" }}>
                      <CheckCircle2 size={10} /> Active
                    </span>
                  ) : (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "11px", fontWeight: 700, color: "#ef4444", background: "rgba(239,68,68,0.1)", padding: "2px 8px", borderRadius: "20px" }}>
                      <XCircle size={10} /> Inactive
                    </span>
                  )}
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "16px" }}>
                  <div>
                    <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Org ID</span>
                    <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)", fontFamily: "monospace", marginTop: "2px" }}>{org.id}</div>
                  </div>
                  {org.org_type && (
                    <div>
                      <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Type</span>
                      <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>{org.org_type}</div>
                    </div>
                  )}
                  {org.ownership_type && (
                    <div>
                      <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Ownership</span>
                      <div style={{ fontSize: "13px", marginTop: "2px" }}>
                        <span style={{ fontWeight: 700, color: org.ownership_type === "GOVERNMENT" ? "#0284c7" : "#7c3aed" }}>
                          {org.ownership_type}
                        </span>
                      </div>
                    </div>
                  )}
                  {org.location && (
                    <div>
                      <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Location</span>
                      <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>{org.location}</div>
                    </div>
                  )}
                  {org.org_code && (
                    <div>
                      <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Code</span>
                      <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)", fontFamily: "monospace", marginTop: "2px" }}>{org.org_code}</div>
                    </div>
                  )}
                  {org.contact_email && (
                    <div>
                      <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Contact</span>
                      <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>{org.contact_email}</div>
                    </div>
                  )}
                </div>
              </div>

              {/* View Overview action */}
              <div style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 12px", background: "var(--clr-surface-2)", borderRadius: "8px", fontSize: "12px", color: "var(--clr-primary)", fontWeight: 600, whiteSpace: "nowrap" }}>
                <ExternalLink size={12} />
                View Overview
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Municipality Org Overview Modal */}
      {selectedOrgForView && (
        <MunicipalityOrgOverview
          orgId={selectedOrgForView.id}
          orgName={selectedOrgForView.name}
          isOpen={Boolean(selectedOrgForView)}
          onClose={() => setSelectedOrgForView(null)}
        />
      )}

      {/* Add Government Organisation Modal */}
      {user?.organisation_id && (
        <AddGovernmentOrgModal
          municipalityId={user.organisation_id}
          municipalityName={municipalityName}
          isOpen={isAddModalOpen}
          onClose={() => setIsAddModalOpen(false)}
          onSuccess={() => {
            if (user.organisation_id) loadAssociatedOrgs(user.organisation_id);
          }}
        />
      )}
    </AppLayout>
  );
}

export default function MunicipalityAssociatedOrgsPage() {
  return (
    <Suspense
      fallback={
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
          <div style={{ color: "var(--clr-text-muted)", fontSize: "14px" }}>Loading associated organisations...</div>
        </div>
      }
    >
      <AssociatedOrgsContent />
    </Suspense>
  );
}