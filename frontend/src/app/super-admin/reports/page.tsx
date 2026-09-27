"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import {
  FileText,
  Download,
  Building,
  Cpu,
  Radio,
  Shield,
  RefreshCw,
} from "lucide-react";

export default function PlatformReportsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [reportData, setReportData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await api.get<any>("/api/v1/super-admin/reports");
      setReportData(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load platform reports", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadReports();
  }, [user]);

  const handleDownloadReport = (title: string) => {
    showToast(`Generating and exporting ${title}...`, "info");
  };

  return (
    <AppLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
            <FileText color="var(--clr-primary)" size={28} />
            Platform Reports
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            Access platform-wide administrative reports, directory exports, and device audits.
          </p>
        </div>

        <button onClick={loadReports} className="btn btn-outline btn-sm" title="Refresh">
          <RefreshCw size={14} className={loading ? "spin" : ""} />
        </button>
      </div>

      {/* Summary KPI Box */}
      {reportData && (
        <div className="card" style={{ padding: "24px", marginBottom: "32px", borderLeft: "4px solid var(--clr-primary)" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "16px" }}>System Metrics Summary</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
            <div>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Total Organisations:</span>
              <div style={{ fontSize: "22px", fontWeight: 800 }}>{reportData.summary.total_organisations}</div>
            </div>
            <div>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Platform Users:</span>
              <div style={{ fontSize: "22px", fontWeight: 800 }}>{reportData.summary.total_users}</div>
            </div>
            <div>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>IoT Devices:</span>
              <div style={{ fontSize: "22px", fontWeight: 800 }}>{reportData.summary.total_iot_devices}</div>
            </div>
            <div>
              <span style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>Total Sensor Readings:</span>
              <div style={{ fontSize: "22px", fontWeight: 800 }}>{reportData.summary.total_sensor_readings}</div>
            </div>
          </div>
        </div>
      )}

      {/* Reports Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "20px" }}>
        {[
          { id: "org_list", title: "Organisation Directory Report", desc: "Complete directory of registered organisations, facility types, and assigned admins." },
          { id: "device_inventory", title: "IoT Device Inventory Report", desc: "Hardware devices, simulators, MAC addresses, and connectivity logs." },
          { id: "sensor_config", title: "Sensor Configuration Audit", desc: "Audit matrix of active vs disabled telemetry modules per facility." },
          { id: "platform_alerts", title: "Platform Security & Anomaly Audit", desc: "Historical anomaly and system alert logs across all facilities." },
          { id: "admin_directory", title: "Admin User Access Report", desc: "Account roles, contact phone numbers, and login activity records." },
        ].map((rep) => (
          <div key={rep.id} className="card" style={{ padding: "24px", display: "flex", flexDirection: "column", justifyContent: "space-between", gap: "16px" }}>
            <div>
              <h3 style={{ fontSize: "17px", fontWeight: 800, color: "var(--clr-text-primary)", marginBottom: "8px" }}>
                {rep.title}
              </h3>
              <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: 0, lineHeight: 1.5 }}>
                {rep.desc}
              </p>
            </div>

            <button
              onClick={() => handleDownloadReport(rep.title)}
              className="btn btn-outline btn-md"
              style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "center" }}
            >
              <Download size={16} />
              <span>Export CSV / PDF</span>
            </button>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
