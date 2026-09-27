"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";
import { api } from "@/lib/api";
import { isMunicipality } from "@/lib/organisation";
import {
  ArrowLeft,
  Layers,
  Zap,
  Droplet,
  Trash2,
  Wind,
  Car,
  ParkingSquare,
  Cpu,
  ShieldCheck,
  Thermometer,
  Lightbulb,
  Activity,
  ChevronRight,
  RefreshCw,
} from "lucide-react";

interface ModuleCardItem {
  id: string;
  metric: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  bg: string;
  border: string;
}

function AllModulesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryOrg = searchParams.get("org");
  const { user, activeOrgId, setActiveOrgId, currentOrg, organisations = [] } = useAuth();
  const { isModuleUnread } = useNotifications();

  // Resolve effective organisation ID
  const effectiveOrgId = React.useMemo(() => {
    if (user?.role === "SUPER_ADMIN") {
      return queryOrg || activeOrgId || user.organisation_id || (organisations.length > 0 ? organisations[0].id : "ORG-00001");
    }
    return user?.organisation_id || null;
  }, [user, activeOrgId, queryOrg, organisations]);

  // Synchronize AuthContext if Super Admin provides queryOrg
  useEffect(() => {
    if (user?.role === "SUPER_ADMIN" && queryOrg && queryOrg !== activeOrgId) {
      setActiveOrgId(queryOrg);
    }
  }, [user, queryOrg, activeOrgId, setActiveOrgId]);

  const [orgData, setOrgData] = useState<any>(null);
  const [kpiData, setKpiData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!effectiveOrgId) return;
    setLoading(true);
    setError(null);
    try {
      const [orgRes, kpiRes] = await Promise.allSettled([
        api.get<any>(`/api/v1/organisations/${effectiveOrgId}`),
        api.get<any>(`/api/v1/dashboard/${effectiveOrgId}`),
      ]);
      if (orgRes.status === "fulfilled") setOrgData(orgRes.value);
      if (kpiRes.status === "fulfilled") setKpiData(kpiRes.value);
    } catch (err: any) {
      setError(err?.message || "Failed to load operational modules.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [effectiveOrgId]);

  const isMunicipalityOrg = isMunicipality(orgData) || isMunicipality(currentOrg) || isMunicipality(kpiData);
  const backLabel = isMunicipalityOrg ? "Back to Municipality Dashboard" : "Back to Dashboard";
  const backHref = effectiveOrgId ? `/dashboard?org=${encodeURIComponent(effectiveOrgId)}` : "/dashboard";

  const allModulesList: ModuleCardItem[] = [
    {
      id: "energy",
      metric: "energy",
      label: isMunicipalityOrg ? "Energy (Own Office)" : "Energy Consumption",
      description: "Grid draw, load balance, peak demand, and renewable generation telemetry.",
      icon: <Zap size={22} color="#f59e0b" />,
      color: "#f59e0b",
      bg: "rgba(245, 158, 11, 0.1)",
      border: "rgba(245, 158, 11, 0.25)",
    },
    {
      id: "water",
      metric: "water",
      label: isMunicipalityOrg ? "Water Supply" : "Water Operations",
      description: "Flow rate, pressure, volumetric consumption, and leak detection.",
      icon: <Droplet size={22} color="#3b82f6" />,
      color: "#3b82f6",
      bg: "rgba(59, 130, 246, 0.1)",
      border: "rgba(59, 130, 246, 0.25)",
    },
    {
      id: "waste",
      metric: "waste",
      label: isMunicipalityOrg ? "Waste Management" : "Waste Telemetry",
      description: "Bin fill level, collection schedules, overflow risk, and diversion rates.",
      icon: <Trash2 size={22} color="#10b981" />,
      color: "#10b981",
      bg: "rgba(16, 185, 129, 0.1)",
      border: "rgba(16, 185, 129, 0.25)",
    },
    {
      id: "air_quality",
      metric: "air_quality",
      label: "Air Quality & Environment",
      description: "Particulate matter PM2.5, PM10, ambient AQI, and pollutant dispersion.",
      icon: <Wind size={22} color="#06b6d4" />,
      color: "#06b6d4",
      bg: "rgba(6, 182, 212, 0.1)",
      border: "rgba(6, 182, 212, 0.25)",
    },
    {
      id: "traffic",
      metric: "traffic",
      label: isMunicipalityOrg ? "Traffic & Mobility" : "Fleet & Movement",
      description: "Corridor density, average transit speed, congestion, and incident logs.",
      icon: <Car size={22} color="#8b5cf6" />,
      color: "#8b5cf6",
      bg: "rgba(139, 92, 246, 0.1)",
      border: "rgba(139, 92, 246, 0.25)",
    },
    {
      id: "parking",
      metric: "parking",
      label: "Parking Utilization",
      description: "Occupancy rate, turnover, bay availability, and EV charge bays.",
      icon: <ParkingSquare size={22} color="#ec4899" />,
      color: "#ec4899",
      bg: "rgba(236, 72, 153, 0.1)",
      border: "rgba(236, 72, 153, 0.25)",
    },
    {
      id: "assets",
      metric: "assets",
      label: "Municipal & Facility Assets",
      description: "Asset condition, vibration, operating hours, and lifecycle health score.",
      icon: <Cpu size={22} color="#14b8a6" />,
      color: "#14b8a6",
      bg: "rgba(20, 184, 166, 0.1)",
      border: "rgba(20, 184, 166, 0.25)",
    },
    {
      id: "safety",
      metric: "safety",
      label: "Safety & Emergency Response",
      description: "Emergency incident rate, fire alarm loop status, and worker hazard telemetry.",
      icon: <ShieldCheck size={22} color="#ef4444" />,
      color: "#ef4444",
      bg: "rgba(239, 68, 68, 0.1)",
      border: "rgba(239, 68, 68, 0.25)",
    },
    {
      id: "climate",
      metric: "climate",
      label: "Indoor Climate & Thermal",
      description: "Ambient zone temperature, humidity index, and HVAC thermal setpoints.",
      icon: <Thermometer size={22} color="#f97316" />,
      color: "#f97316",
      bg: "rgba(249, 115, 22, 0.1)",
      border: "rgba(249, 115, 22, 0.25)",
    },
    ...(isMunicipalityOrg
      ? [
          {
            id: "street_lighting",
            metric: "street_lighting",
            label: "Street Lighting",
            description: "Luminaire uptime, dynamic dimming schedule, and circuit faults.",
            icon: <Lightbulb size={22} color="#eab308" />,
            color: "#eab308",
            bg: "rgba(234, 179, 8, 0.1)",
            border: "rgba(234, 179, 8, 0.25)",
          },
          {
            id: "roads",
            metric: "roads",
            label: "Roads & Infrastructure",
            description: "Pavement condition index, roadwork status, and lane clearances.",
            icon: <Activity size={22} color="#6366f1" />,
            color: "#6366f1",
            bg: "rgba(99, 102, 241, 0.1)",
            border: "rgba(99, 102, 241, 0.25)",
          },
        ]
      : []),
  ];

  return (
    <AppLayout>
      <div style={{ maxWidth: "1280px", margin: "0 auto", paddingBottom: "40px" }}>
        {/* Navigation Breadcrumb */}
        <div style={{ marginBottom: "20px" }}>
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
            <ArrowLeft size={16} /> {backLabel}
          </Link>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "12px",
                  background: "rgba(16, 185, 129, 0.15)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Layers size={24} color="var(--clr-primary)" />
              </div>
              <div>
                <h1 style={{ fontSize: "24px", fontWeight: 800, color: "var(--clr-text-primary)", margin: 0 }}>
                  Operational Modules Directory
                </h1>
                <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", margin: "4px 0 0 0" }}>
                  Active telemetry domains for {orgData?.name || effectiveOrgId || "Organisation"}
                </p>
              </div>
            </div>

            <button
              onClick={loadData}
              disabled={loading}
              className="btn btn-outline btn-sm"
              style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
            </button>
          </div>
        </div>

        {error && (
          <div
            style={{
              padding: "14px 18px",
              borderRadius: "8px",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#ef4444",
              marginBottom: "20px",
              fontSize: "13px",
            }}
          >
            {error}
          </div>
        )}

        {/* Modules Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "16px" }}>
          {allModulesList.map((mod) => {
            const hasUnread = isModuleUnread(mod.metric);
            const detailHref = effectiveOrgId
              ? `/dashboard/modules/${mod.id}?org=${encodeURIComponent(effectiveOrgId)}`
              : `/dashboard/modules/${mod.id}`;

            return (
              <Link
                key={mod.id}
                href={detailHref}
                style={{
                  position: "relative",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  padding: "20px",
                  borderRadius: "14px",
                  background: "var(--clr-surface-2, rgba(255, 255, 255, 0.03))",
                  border: hasUnread ? "1px solid rgba(239, 68, 68, 0.4)" : `1px solid var(--clr-border, #334155)`,
                  textDecoration: "none",
                  transition: "all 0.2s ease",
                  gap: "14px",
                  boxShadow: hasUnread ? "0 0 12px rgba(239, 68, 68, 0.15)" : undefined,
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <div
                        style={{
                          width: "40px",
                          height: "40px",
                          borderRadius: "10px",
                          background: mod.bg,
                          border: `1px solid ${mod.border}`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        {mod.icon}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "16px", fontWeight: 700, color: "var(--clr-text-primary)" }}>
                          {mod.label}
                        </span>
                        {hasUnread && (
                          <RedDotIndicator size="sm" label={`${mod.label} — unread anomaly`} />
                        )}
                      </div>
                    </div>
                  </div>

                  <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: 0, lineHeight: 1.5 }}>
                    {mod.description}
                  </p>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingTop: "12px",
                    borderTop: "1px solid var(--clr-border-light, rgba(255, 255, 255, 0.05))",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "var(--clr-primary)",
                  }}
                >
                  <span>Open Intelligence & Drill-down</span>
                  <ChevronRight size={16} />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
}

export default function AllModulesPage() {
  return (
    <Suspense
      fallback={
        <AppLayout>
          <div style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
            Loading modules directory...
          </div>
        </AppLayout>
      }
    >
      <AllModulesContent />
    </Suspense>
  );
}
