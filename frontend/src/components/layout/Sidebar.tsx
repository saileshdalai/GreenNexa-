"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useDemo } from "@/context/DemoContext";
import { isMunicipality } from "@/lib/organisation";
import { api } from "@/lib/api";
import {
  LayoutDashboard,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  MessageSquare,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  PlusCircle,
  Building2,
  Users,
  RadioTower,
  Cpu,
  Activity,
  Bell,
  SlidersHorizontal,
  ArrowLeft,
  Layers,
  MapPin,
} from "lucide-react";
import { useNotifications } from "@/context/NotificationContext";
import { RedDotIndicator } from "@/components/ui/RedDotIndicator";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  hasRedDot?: boolean;
  redDotLabel?: string;
  subItems?: { label: string; href: string; metric?: string; hasRedDot?: boolean; redDotLabel?: string }[];
}

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const pathname = usePathname();
  const { user, activeOrgId, currentOrg, enabledModules: authEnabledModules } = useAuth();
  const { presentationModeActive } = useDemo();
  const { isModuleUnread, isSectionUnread, totalUnread } = useNotifications();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [createMenuOpen, setCreateMenuOpen] = useState<boolean>(false);
  const [modulesMenuOpen, setModulesMenuOpen] = useState<boolean>(true);

  // Authoritative Municipality detection and module visibility
  const isMunicipalityOrg = currentOrg ? isMunicipality(currentOrg) : false;
  const effectiveModules = (currentOrg?.enabled_modules && currentOrg.enabled_modules.length > 0)
    ? currentOrg.enabled_modules
    : authEnabledModules;

  if (presentationModeActive) {
    return null;
  }

  const isSuperAdmin = user?.role === "SUPER_ADMIN";
  const isSuperAdminRoute = pathname.startsWith("/super-admin");

  useEffect(() => {
    if (!user) return;
    const checkUnread = async () => {
      try {
        const data = await api.get<{ unread_count: number }>("/api/v1/messages/unread-count");
        setUnreadCount(data.unread_count || 0);
      } catch { }
    };
    checkUnread();
    const interval = setInterval(checkUnread, 30000);
    return () => clearInterval(interval);
  }, [user]);

  const hasAnyModuleUnread =
    isModuleUnread("energy") ||
    isModuleUnread("water") ||
    isModuleUnread("waste") ||
    isModuleUnread("air_quality") ||
    isModuleUnread("traffic") ||
    isModuleUnread("parking") ||
    isModuleUnread("assets") ||
    isModuleUnread("safety") ||
    isModuleUnread("climate") ||
    isModuleUnread("street_lighting") ||
    isModuleUnread("roads") ||
    isModuleUnread("parks") ||
    isModuleUnread("sewage");

  // Core nav items for ADMIN / Org view (focusing on non-duplicate operational management)
  const adminNavItems: NavItem[] = [
    { href: "/dashboard", label: "Overview", icon: <LayoutDashboard size={18} /> },
    {
      href: "/dashboard/modules",
      label: "Modules",
      icon: <Layers size={18} />,
      hasRedDot: hasAnyModuleUnread,
      redDotLabel: "Operational Modules — new unseen activity",
      subItems: [
        { label: isMunicipalityOrg ? "Energy (Own Office)" : "Energy", href: "/dashboard/modules/energy", metric: "energy", hasRedDot: isModuleUnread("energy"), redDotLabel: "Energy — new unseen activity" },
        { label: isMunicipalityOrg ? "Water Supply" : "Water", href: "/dashboard/modules/water", metric: "water", hasRedDot: isModuleUnread("water"), redDotLabel: "Water — new unseen activity" },
        { label: isMunicipalityOrg ? "Waste Management" : "Waste", href: "/dashboard/modules/waste", metric: "waste", hasRedDot: isModuleUnread("waste"), redDotLabel: "Waste — new unseen activity" },
        { label: "Air Quality", href: "/dashboard/modules/air_quality", metric: "air_quality", hasRedDot: isModuleUnread("air_quality"), redDotLabel: "Air Quality — new unseen activity" },
        { label: isMunicipalityOrg ? "Traffic & Parking" : "Traffic", href: "/dashboard/modules/traffic", metric: "traffic", hasRedDot: isModuleUnread("traffic"), redDotLabel: "Traffic — new unseen activity" },
        { label: "Parking", href: "/dashboard/modules/parking", metric: "parking", hasRedDot: isModuleUnread("parking"), redDotLabel: "Parking — new unseen activity" },
        { label: "Municipal Assets", href: "/dashboard/modules/assets", metric: "assets", hasRedDot: isModuleUnread("assets"), redDotLabel: "Assets — new unseen activity" },
        { label: "Safety & Incidents", href: "/dashboard/modules/safety", metric: "safety", hasRedDot: isModuleUnread("safety"), redDotLabel: "Safety — new unseen activity" },
        { label: "Climate & Environment", href: "/dashboard/modules/climate", metric: "climate", hasRedDot: isModuleUnread("climate"), redDotLabel: "Climate — new unseen activity" },
        ...(isMunicipalityOrg
          ? [
              { label: "Street Lighting", href: "/dashboard/modules/street_lighting", metric: "street_lighting", hasRedDot: isModuleUnread("street_lighting"), redDotLabel: "Street Lighting — new unseen activity" },
              { label: "Roads & Infrastructure", href: "/dashboard/modules/roads", metric: "roads", hasRedDot: isModuleUnread("roads"), redDotLabel: "Roads & Infrastructure — new unseen activity" },
              { label: "Parks & Playgrounds", href: "/dashboard/modules/parks", metric: "parks", hasRedDot: isModuleUnread("parks"), redDotLabel: "Parks & Playgrounds — new unseen activity" },
              { label: "Drainage & Sewage", href: "/dashboard/modules/sewage", metric: "sewage", hasRedDot: isModuleUnread("sewage"), redDotLabel: "Drainage & Sewage — new unseen activity" },
            ]
          : []),
      // Filter by enabled_modules if we have data; fall back to showing all if not yet loaded
      ].filter((sub) => !effectiveModules || !sub.metric || effectiveModules.includes(sub.metric)),
    },
    { href: "/forecast", label: "AI Forecast", icon: <TrendingUp size={18} /> },
    {
      href: "/anomalies",
      label: "Anomalies",
      icon: <AlertTriangle size={18} />,
      hasRedDot: isSectionUnread("anomalies") || totalUnread > 0,
      redDotLabel: `Anomalies — ${totalUnread} unread event${totalUnread === 1 ? "" : "s"}`,
    },
    {
      href: "/recommendations",
      label: "Recommendations",
      icon: <Lightbulb size={18} />,
      hasRedDot: isSectionUnread("recommendations"),
      redDotLabel: "Recommendations — new insights available",
    },
    { href: "/messages", label: "Messages", icon: <MessageSquare size={18} />, badge: unreadCount },
    { href: "/reports", label: "Reports", icon: <FileText size={18} /> },
    { href: "/settings", label: "Settings", icon: <Settings size={18} /> },
  ];

  // Platform Management nav items for SUPER_ADMIN
  const superAdminNavItems: NavItem[] = [
    { href: "/super-admin", label: "Platform Overview", icon: <LayoutDashboard size={18} /> },
    {
      href: "/super-admin/create",
      label: "Create",
      icon: <PlusCircle size={18} />,
      subItems: [
        { label: "Organisation", href: "/super-admin/create?entity=organisation" },
        { label: "Facility", href: "/super-admin/create?entity=facility" },
      ],
    },
    { href: "/super-admin/organisations", label: "Organisations", icon: <Building2 size={18} /> },
    { href: "/super-admin/users", label: "Users / Admins", icon: <Users size={18} /> },
    { href: "/super-admin/sensors", label: "Sensor Configuration", icon: <RadioTower size={18} /> },
    { href: "/super-admin/iot", label: "IoT Devices", icon: <Cpu size={18} /> },
    { href: "/super-admin/monitoring", label: "Organisation Monitoring", icon: <Activity size={18} /> },
    { href: "/super-admin/alerts", label: "Platform Alerts", icon: <Bell size={18} /> },
    { href: "/super-admin/reports", label: "Reports", icon: <FileText size={18} /> },
    { href: "/super-admin/settings", label: "Platform Settings", icon: <SlidersHorizontal size={18} /> },
  ];

  const currentNavItems = isSuperAdmin && (isSuperAdminRoute || !pathname.startsWith("/dashboard"))
    ? superAdminNavItems
    : isSuperAdmin && pathname.startsWith("/dashboard")
      ? adminNavItems
      : isSuperAdmin
        ? superAdminNavItems
        : adminNavItems;

  return (
    <aside
      className={`app-sidebar ${collapsed ? "app-sidebar-collapsed" : ""}`}
      style={{
        width: collapsed ? "60px" : "240px",
        height: "calc(100vh - 72px)",
        position: "sticky",
        top: "72px",
        backgroundColor: "var(--clr-surface)",
        borderRight: "1px solid var(--clr-border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        transition: "width 0.2s ease-in-out",
        zIndex: 40,
        flexShrink: 0,
      }}
    >
      <div style={{ padding: "16px 12px", overflowY: "auto" }}>
        {/* Super Admin header tag */}
        {isSuperAdmin && !collapsed && (
          <div style={{ marginBottom: "16px", padding: "0 6px" }}>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 800,
                letterSpacing: "0.08em",
                color: "var(--clr-primary)",
                textTransform: "uppercase",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "4px 8px",
                background: "var(--clr-primary-light)",
                borderRadius: "6px",
              }}
            >
              <ShieldCheck size={14} />
              <span>SUPER ADMIN PLATFORM</span>
            </div>
          </div>
        )}

        {/* Super Admin quick switch back to Platform Overview if viewing org dashboard */}
        {isSuperAdmin && pathname.startsWith("/dashboard") && !collapsed && (
          <Link
            href="/super-admin"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 12px",
              marginBottom: "12px",
              borderRadius: "8px",
              fontSize: "12px",
              fontWeight: 700,
              backgroundColor: "#10b98115",
              color: "#10b981",
              border: "1px solid #10b98130",
              textDecoration: "none",
            }}
          >
            <ArrowLeft size={14} />
            <span>Back to Platform Overview</span>
          </Link>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {currentNavItems.map((item) => {
            const orgSuffix = activeOrgId && !item.href.startsWith("/super-admin") ? `?org=${encodeURIComponent(activeOrgId)}` : "";
            const itemHref = item.href.includes("?org=") ? item.href : `${item.href}${orgSuffix}`;
            const isActive = pathname === item.href || (item.href !== "/super-admin" && pathname.startsWith(item.href));
            const hasSub = !!item.subItems;
            const isSubOpen = (item.label === "Create" && (isActive || createMenuOpen)) ||
                              (item.label === "Modules" && (pathname.startsWith("/dashboard/modules") || modulesMenuOpen));

            return (
              <div key={item.label}>
                <Link
                  href={itemHref}
                  onClick={(e) => {
                    if (hasSub && !collapsed) {
                      if (item.label === "Create") setCreateMenuOpen((prev) => !prev);
                      else if (item.label === "Modules") setModulesMenuOpen((prev) => !prev);
                    }
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: collapsed ? "center" : "space-between",
                    padding: collapsed ? "10px" : "10px 14px",
                    borderRadius: "10px",
                    fontSize: "14px",
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? "var(--clr-primary)" : "var(--clr-text-secondary)",
                    backgroundColor: isActive ? "var(--clr-primary-light)" : "transparent",
                    textDecoration: "none",
                    transition: "all 0.15s ease",
                    position: "relative",
                  }}
                  title={collapsed ? (item.hasRedDot ? `${item.label} (${item.redDotLabel || "New unseen activity"})` : item.label) : undefined}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", position: "relative" }}>
                    <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                      <span style={{ color: isActive ? "var(--clr-primary)" : "var(--clr-text-muted)" }}>
                        {item.icon}
                      </span>
                      {collapsed && item.hasRedDot && (
                        <div style={{ position: "absolute", top: "-4px", right: "-4px" }}>
                          <RedDotIndicator label={item.redDotLabel || `${item.label} — new unseen activity`} size="sm" />
                        </div>
                      )}
                    </div>
                    {!collapsed && <span>{item.label}</span>}
                  </div>

                  {!collapsed && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      {item.hasRedDot && !item.badge && (
                        <RedDotIndicator label={item.redDotLabel || `${item.label} — new unseen activity`} size="md" />
                      )}
                      {item.badge && item.badge > 0 ? (
                        <span
                          style={{
                            background: "var(--clr-error)",
                            color: "#fff",
                            borderRadius: "9999px",
                            padding: "2px 6px",
                            fontSize: "11px",
                            fontWeight: 700,
                            lineHeight: 1,
                          }}
                        >
                          {item.badge}
                        </span>
                      ) : null}
                    </div>
                  )}
                </Link>

                {/* Submenu for Create / Modules */}
                {hasSub && !collapsed && isSubOpen && (
                  <div
                    style={{
                      marginLeft: "28px",
                      marginTop: "4px",
                      marginBottom: "6px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "2px",
                      borderLeft: "2px solid var(--clr-border)",
                      paddingLeft: "8px",
                    }}
                  >
                    {item.subItems?.map((sub) => {
                      const isSubActive = pathname === sub.href;
                      const subHref = sub.href.includes("?org=") ? sub.href : `${sub.href}${orgSuffix}`;
                      return (
                        <Link
                          key={sub.label}
                          href={subHref}
                          style={{
                            fontSize: "12px",
                            padding: "5px 8px",
                            borderRadius: "6px",
                            color: isSubActive ? "var(--clr-primary)" : "var(--clr-text-secondary)",
                            backgroundColor: isSubActive ? "var(--clr-primary-light)" : "transparent",
                            textDecoration: "none",
                            fontWeight: isSubActive ? 700 : 500,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                          }}
                        >
                          <span>{sub.label}</span>
                          {sub.hasRedDot && (
                            <RedDotIndicator label={sub.redDotLabel || `${sub.label} — new unseen activity`} size="sm" />
                          )}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer / Toggle & Role badge */}
      <div
        style={{
          padding: "12px",
          borderTop: "1px solid var(--clr-border-light)",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "space-between",
        }}
      >
        {!collapsed && user && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
            <ShieldCheck size={16} color="var(--clr-primary)" />
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--clr-text-primary)" }}>
                {user.role}
              </span>
              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {user.role === "SUPER_ADMIN" ? "Platform Administrator" : (user.organisation_id || "System")}
              </span>
            </div>
          </div>
        )}

        <button
          onClick={onToggle}
          style={{
            padding: "6px",
            borderRadius: "6px",
            border: "1px solid var(--clr-border)",
            background: "var(--clr-surface-2)",
            color: "var(--clr-text-secondary)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  );
}
