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
  Activity,
  Eye,
  Building2,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  RefreshCw,
  Search,
} from "lucide-react";

export default function OrganisationMonitoringPage() {
  const { user, setActiveOrgId } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [orgs, setOrgs] = useState<OrganisationOverviewItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");

  const loadOrgs = async () => {
    setLoading(true);
    try {
      const res = await api.get<{ organisations: OrganisationOverviewItem[] }>("/api/v1/super-admin/overview");
      setOrgs(res.organisations || []);
    } catch (err: any) {
      showToast(err.message || "Failed to load organisation monitoring status", "error");
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

  const handleLaunchDashboard = (orgId: string, orgName: string) => {
    setActiveOrgId(orgId);
    showToast(`Launching operational telemetry dashboard for ${orgName}`, "info");
    router.push("/dashboard");
  };

  const filtered = orgs.filter((o) =>
    o.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.facility_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <AppLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
            <Activity color="var(--clr-primary)" size={28} />
            Organisation Operational Monitoring
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            Super Admin quick-launcher to open any organisation's operational dashboard without altering data.
          </p>
        </div>

        <button onClick={loadOrgs} className="btn btn-outline btn-sm" title="Refresh">
          <RefreshCw size={14} className={loading ? "spin" : ""} />
        </button>
      </div>

      {/* Filter */}
      <div className="card" style={{ padding: "20px", marginBottom: "24px" }}>
        <div style={{ position: "relative" }}>
          <Search size={16} color="var(--clr-text-muted)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            className="form-input"
            placeholder="Search facility by name, ID, or type..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ paddingLeft: "36px" }}
          />
        </div>
      </div>

      {/* Organisation Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "20px" }}>
        {filtered.map((org) => (
          <div key={org.id} className="card" style={{ padding: "24px", display: "flex", flexDirection: "column", justifyContent: "space-between", gap: "20px" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--clr-primary)", background: "var(--clr-primary-light)", padding: "2px 8px", borderRadius: "6px", fontFamily: "monospace" }}>
                  {org.id}
                </span>
                <span style={{ fontSize: "12px", fontWeight: 700, padding: "2px 8px", borderRadius: "9999px", background: org.status === "Active" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)", color: org.status === "Active" ? "#10b981" : "#ef4444" }}>
                  {org.status}
                </span>
              </div>

              <h2 style={{ fontSize: "18px", fontWeight: 800, color: "var(--clr-text-primary)", marginBottom: "4px" }}>
                {org.name}
              </h2>
              <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginBottom: "16px" }}>
                {org.facility_type} • {org.location}
              </div>

              <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginBottom: "16px" }}>
                {org.enabled_modules.map((m) => (
                  <span key={m} style={{ fontSize: "10px", fontWeight: 700, padding: "2px 6px", borderRadius: "4px", background: "var(--clr-surface-2)", border: "1px solid var(--clr-border)", textTransform: "capitalize" }}>
                    {m.replace("_", " ")}
                  </span>
                ))}
              </div>

              <div style={{ fontSize: "12px", color: "var(--clr-text-muted)", display: "flex", alignItems: "center", gap: "6px" }}>
                <Cpu size={14} />
                <span>{org.iot_devices_count} IoT devices registered</span>
              </div>
            </div>

            <button
              onClick={() => handleLaunchDashboard(org.id, org.name)}
              className="btn btn-primary btn-md"
              style={{ width: "100%", justifyContent: "center", gap: "8px", fontWeight: 700 }}
            >
              <Eye size={16} />
              <span>Open Organisation Dashboard</span>
            </button>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
