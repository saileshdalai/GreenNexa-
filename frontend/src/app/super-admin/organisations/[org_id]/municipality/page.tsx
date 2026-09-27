"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { GovernmentOrgItem } from "@/types";
import {
  ArrowLeft,
  MapPin,
  Building2,
  Plus,
  Trash2,
  Save,
  RefreshCw,
  CheckSquare,
  Square,
} from "lucide-react";

type Ward = {
  id: string;
  municipality_id: string;
  ward_number: string;
  ward_name: string;
  zone?: string | null;
  population?: number | null;
  area_sq_km?: number | null;
  is_active: boolean;
};

type Tab = "wards" | "associations";

export default function MunicipalityManagePage() {
  const params = useParams();
  const org_id = params?.org_id as string;
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<Tab>("wards");
  const [orgName, setOrgName] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const [wards, setWards] = useState<Ward[]>([]);
  const [newWardName, setNewWardName] = useState("");
  const [wardLoading, setWardLoading] = useState(false);

  const [govOrgs, setGovOrgs] = useState<GovernmentOrgItem[]>([]);
  const [selectedGovIds, setSelectedGovIds] = useState<Set<string>>(new Set());
  const [assocLoading, setAssocLoading] = useState(false);
  const [assocSaving, setAssocSaving] = useState(false);
  const [govSearch, setGovSearch] = useState("");

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadAll();
  }, [user, org_id]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const wardsRes = await api.get<{ items: Ward[] }>(`/api/v1/organisations/${org_id}/wards?active_only=false`).catch(() => null);
      setWards((wardsRes as any)?.items || []);
      try {
        const fullCfg = await api.get<any>(`/api/v1/super-admin/organisations/${org_id}`);
        setOrgName(fullCfg?.organisation_name || fullCfg?.name || org_id);
      } catch {
        try {
          const plain = await api.get<any>(`/api/v1/organisations/${org_id}`);
          setOrgName(plain?.name || org_id);
        } catch {
          setOrgName(org_id);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const loadAssociations = async () => {
    setAssocLoading(true);
    try {
      const [govRes, assocRes] = await Promise.allSettled([
        api.get<GovernmentOrgItem[]>("/api/v1/super-admin/organisations/government"),
        api.get<{ associated_gov_org_ids: string[] }>(`/api/v1/super-admin/organisations/${org_id}/municipality-associations`),
      ]);
      if (govRes.status === "fulfilled") setGovOrgs((govRes as any).value || []);
      if (assocRes.status === "fulfilled") setSelectedGovIds(new Set((assocRes as any).value?.associated_gov_org_ids || []));
    } catch (err: any) {
      showToast(err.message || "Failed to load government organisations", "error");
    } finally {
      setAssocLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "associations" && govOrgs.length === 0 && !assocLoading) {
      loadAssociations();
    }
  }, [activeTab]);

  const handleAddWard = async () => {
    const name = newWardName.trim();
    if (!name) return showToast("Ward name cannot be empty.", "error");
    setWardLoading(true);
    try {
      await api.post(`/api/v1/organisations/${org_id}/wards`, { ward_name: name });
      setNewWardName("");
      showToast(`Ward created successfully.`, "success");
      const res = await api.get<{ items: Ward[] }>(`/api/v1/organisations/${org_id}/wards?active_only=false`);
      setWards(res?.items || []);
    } catch (err: any) {
      showToast(err.message || "Failed to create ward.", "error");
    } finally {
      setWardLoading(false);
    }
  };

  const handleRemoveWard = async (wardId: string, wardName: string) => {
    setWardLoading(true);
    try {
      await api.delete(`/api/v1/organisations/${org_id}/wards/${wardId}`);
      showToast(`Ward deactivated.`, "success");
      const res = await api.get<{ items: Ward[] }>(`/api/v1/organisations/${org_id}/wards?active_only=false`);
      setWards(res?.items || []);
    } catch (err: any) {
      showToast(err.message || "Failed to remove ward.", "error");
    } finally {
      setWardLoading(false);
    }
  };

  const toggleGovOrg = (id: string) => {
    setSelectedGovIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSaveAssociations = async () => {
    setAssocSaving(true);
    try {
      await api.put(`/api/v1/super-admin/organisations/${org_id}/municipality-associations`, {
        associated_gov_org_ids: Array.from(selectedGovIds),
      });
      showToast("Associations saved successfully.", "success");
    } catch (err: any) {
      showToast(err.message || "Failed to save associations.", "error");
    } finally {
      setAssocSaving(false);
    }
  };

  const filteredGovOrgs = govOrgs.filter((o) =>
    o.name.toLowerCase().includes(govSearch.toLowerCase()) ||
    (o.org_type || "").toLowerCase().includes(govSearch.toLowerCase()) ||
    (o.location || "").toLowerCase().includes(govSearch.toLowerCase())
  );

  return (
    <AppLayout>
      <div style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
        <Link href="/super-admin" style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--clr-text-muted)", textDecoration: "none", fontSize: "13px" }}>
          <ArrowLeft size={14} />
          Super Admin
        </Link>
        <span style={{ color: "var(--clr-text-muted)" }}>›</span>
        <span style={{ fontSize: "13px", color: "var(--clr-text-secondary)" }}>Municipality Management</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "24px" }}>
        <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(2, 132, 199, 0.15)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <MapPin size={20} color="#0284c7" />
        </div>
        <div>
          <h1 style={{ fontSize: "22px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
            {loading ? "Loading..." : orgName}
          </h1>
          <p style={{ fontSize: "13px", color: "var(--clr-text-muted)", margin: "2px 0 0" }}>
            Municipality — Wards and Government Org Associations
          </p>
        </div>
      </div>

      <div style={{ display: "flex", borderBottom: "2px solid var(--clr-border)", marginBottom: "24px" }}>
        {(["wards", "associations"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "10px 22px", fontWeight: 700, fontSize: "14px", border: "none", background: "none", cursor: "pointer",
              borderBottom: activeTab === tab ? "2px solid #0284c7" : "2px solid transparent",
              marginBottom: "-2px",
              color: activeTab === tab ? "#0284c7" : "var(--clr-text-muted)",
            }}
          >
            {tab === "wards" ? "Wards" : "Government Associations"}
          </button>
        ))}
      </div>

      {activeTab === "wards" && (
        <div>
          <div style={{ background: "var(--clr-surface-1)", border: "1px solid var(--clr-border)", borderRadius: "12px", padding: "20px", marginBottom: "24px" }}>
            <h3 style={{ margin: "0 0 14px", fontSize: "15px", fontWeight: 700, color: "var(--clr-text-primary)" }}>Add New Ward</h3>
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <input
                type="text"
                value={newWardName}
                onChange={(e) => setNewWardName(e.target.value)}
                placeholder="e.g. Ward 1 - North Zone"
                onKeyDown={(e) => e.key === "Enter" && handleAddWard()}
                style={{ flex: 1, padding: "9px 14px", borderRadius: "8px", border: "1px solid var(--clr-border)", background: "var(--clr-surface-2)", color: "var(--clr-text-primary)", fontSize: "14px" }}
              />
              <button
                onClick={handleAddWard}
                disabled={wardLoading || !newWardName.trim()}
                className="btn btn-primary btn-sm"
                style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "9px 16px" }}
              >
                {wardLoading ? <RefreshCw size={14} /> : <Plus size={14} />}
                Add Ward
              </button>
            </div>
          </div>

          {loading ? (
            <p style={{ color: "var(--clr-text-muted)" }}>Loading wards...</p>
          ) : wards.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--clr-text-muted)" }}>
              <MapPin size={32} style={{ marginBottom: "10px", opacity: 0.4 }} />
              <p>No wards configured yet.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {wards.map((ward) => (
                <div
                  key={ward.id}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 18px", background: "var(--clr-surface-1)", border: "1px solid var(--clr-border)", borderRadius: "10px" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--clr-text-muted)", background: "var(--clr-surface-2)", padding: "3px 8px", borderRadius: "6px" }}>Ward {ward.ward_number}</span>
                    <span style={{ fontWeight: 600, color: "var(--clr-text-primary)" }}>{ward.ward_name}</span>
                    {!ward.is_active && (
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "#f59e0b", background: "rgba(245,158,11,0.1)", padding: "2px 7px", borderRadius: "5px" }}>INACTIVE</span>
                    )}
                  </div>
                  <button
                    onClick={() => handleRemoveWard(ward.id, ward.ward_name)}
                    className="btn btn-outline btn-sm"
                    style={{ padding: "5px 10px", color: "#ef4444", borderColor: "rgba(239,68,68,0.3)" }}
                    disabled={wardLoading}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "associations" && (
        <div>
          <div style={{ marginBottom: "16px", display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "var(--clr-text-primary)" }}>Associate Government Organisations</h3>
              <p style={{ margin: "4px 0 0", fontSize: "13px", color: "var(--clr-text-muted)" }}>
                Selected organisations will be visible (read-only) to the Municipality Admin.
              </p>
            </div>
            <button onClick={handleSaveAssociations} disabled={assocSaving} className="btn btn-primary btn-sm" style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
              {assocSaving ? <RefreshCw size={14} /> : <Save size={14} />}
              Save Associations
            </button>
          </div>

          <input
            type="text"
            value={govSearch}
            onChange={(e) => setGovSearch(e.target.value)}
            placeholder="Search government organisations..."
            style={{ width: "100%", padding: "9px 14px", borderRadius: "8px", border: "1px solid var(--clr-border)", background: "var(--clr-surface-2)", color: "var(--clr-text-primary)", fontSize: "14px", marginBottom: "14px", boxSizing: "border-box" }}
          />

          {assocLoading ? (
            <p style={{ color: "var(--clr-text-muted)" }}>Loading...</p>
          ) : filteredGovOrgs.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px", color: "var(--clr-text-muted)" }}>
              <Building2 size={32} style={{ marginBottom: "10px", opacity: 0.4 }} />
              <p>No GOVERNMENT-owned organisations found on this platform.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {filteredGovOrgs.map((gov) => {
                const checked = selectedGovIds.has(gov.id);
                return (
                  <div
                    key={gov.id}
                    onClick={() => toggleGovOrg(gov.id)}
                    style={{
                      display: "flex", alignItems: "center", gap: "12px", padding: "12px 18px",
                      background: checked ? "rgba(2,132,199,0.08)" : "var(--clr-surface-1)",
                      border: `1px solid ${checked ? "#0284c7" : "var(--clr-border)"}`,
                      borderRadius: "10px", cursor: "pointer",
                    }}
                  >
                    {checked ? <CheckSquare size={18} color="#0284c7" /> : <Square size={18} color="var(--clr-text-muted)" />}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, color: "var(--clr-text-primary)", fontSize: "14px" }}>{gov.name}</div>
                      <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", marginTop: "2px" }}>
                        {gov.id}{gov.org_type ? ` - ${gov.org_type}` : ""}{gov.location ? ` - ${gov.location}` : ""}
                      </div>
                    </div>
                    {!gov.is_active && (
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "#f59e0b", background: "rgba(245,158,11,0.1)", padding: "2px 7px", borderRadius: "5px" }}>INACTIVE</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {selectedGovIds.size > 0 && (
            <div style={{ marginTop: "16px", padding: "12px 16px", background: "rgba(2,132,199,0.08)", borderRadius: "8px", fontSize: "13px", color: "#0284c7", fontWeight: 600 }}>
              {selectedGovIds.size} government organisation{selectedGovIds.size !== 1 ? "s" : ""} selected
            </div>
          )}
        </div>
      )}
    </AppLayout>
  );
}