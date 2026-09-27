"use client";

/**
 * GreenNexa — Dashboard "..." options menu.
 *
 * Present on every dashboard (facility and municipality). It hosts the
 * Dashboard Style selector and, for municipalities, the existing Add → Ward /
 * Add → Organisation actions so they remain reachable from the dashboard itself
 * as well as from the global header menu.
 */

import React, { useEffect, useRef, useState } from "react";
import { Building2, ChevronRight, MoreHorizontal, MapPin } from "lucide-react";
import { DashboardStyleMenu } from "./DashboardStyleMenu";
import { AddWardModal } from "@/components/municipality/AddWardModal";
import { AddGovernmentOrgModal } from "@/components/municipality/AddGovernmentOrgModal";
import { useAuth } from "@/context/AuthContext";
import { isMunicipality } from "@/lib/organisation";

const menuItemStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "10px",
  width: "100%",
  padding: "9px 14px",
  background: "transparent",
  border: "none",
  color: "var(--clr-text-primary)",
  fontSize: "13px",
  fontFamily: "inherit",
  cursor: "pointer",
  textAlign: "left",
  borderRadius: "8px",
};

export function DashboardOptionsMenu({
  organisationId,
  organisationName,
  showAddActions = false,
}: {
  organisationId: string;
  organisationName?: string;
  showAddActions?: boolean;
}) {
  const { currentOrg } = useAuth();
  const [open, setOpen] = useState(false);
  const [wardModalOpen, setWardModalOpen] = useState(false);
  const [govOrgModalOpen, setGovOrgModalOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const org = currentOrg && currentOrg.id === organisationId ? currentOrg : null;
  const canAdd = Boolean(showAddActions && org && isMunicipality(org));

  useEffect(() => {
    if (!open) return;
    const onClickOutside = (event: MouseEvent | TouchEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("touchstart", onClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("touchstart", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <button
        ref={triggerRef}
        type="button"
        id="dashboard-options-menu-btn"
        data-dashboard-options-trigger
        onClick={(e) => {
          e.stopPropagation();
          setOpen((prev) => !prev);
        }}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls="dashboard-options-menu-dropdown"
        aria-label="Dashboard options menu"
        title="Dashboard options (⋯)"
        className="btn btn-outline btn-sm"
        style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
      >
        <MoreHorizontal size={16} />
        <span>Options</span>
      </button>

      {open && (
        <div
          id="dashboard-options-menu-dropdown"
          role="menu"
          aria-label="Dashboard options"
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 6px)",
            zIndex: 200,
            minWidth: "290px",
            maxHeight: "70vh",
            overflowY: "auto",
            padding: "6px",
            borderRadius: "12px",
            background: "var(--clr-surface-1, var(--clr-surface))",
            border: "1px solid var(--clr-border)",
            boxShadow: "0 18px 40px -12px rgba(0,0,0,0.55)",
          }}
        >
          <DashboardStyleMenu onSelected={() => setOpen(false)} />

          {canAdd && (
            <div>
              <div
                style={{
                  padding: "6px 14px 4px",
                  fontSize: "11px",
                  fontWeight: 800,
                  color: "var(--clr-text-muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Add
              </div>
              <button
                type="button"
                role="menuitem"
                data-dashboard-add="ward"
                style={menuItemStyle}
                onClick={() => {
                  setOpen(false);
                  setWardModalOpen(true);
                }}
              >
                <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                  <MapPin size={15} style={{ color: "#0284c7" }} />
                  Ward
                </span>
                <ChevronRight size={13} style={{ color: "var(--clr-text-muted)" }} />
              </button>
              <button
                type="button"
                role="menuitem"
                data-dashboard-add="organisation"
                style={menuItemStyle}
                onClick={() => {
                  setOpen(false);
                  setGovOrgModalOpen(true);
                }}
              >
                <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                  <Building2 size={15} style={{ color: "var(--clr-primary)" }} />
                  Organisation
                </span>
                <ChevronRight size={13} style={{ color: "var(--clr-text-muted)" }} />
              </button>
            </div>
          )}
        </div>
      )}

      {canAdd && org && (
        <>
          <AddWardModal
            municipalityId={org.id}
            municipalityName={org.name || organisationName || organisationId}
            isOpen={wardModalOpen}
            onClose={() => setWardModalOpen(false)}
          />
          <AddGovernmentOrgModal
            municipalityId={org.id}
            municipalityName={org.name || organisationName || organisationId}
            isOpen={govOrgModalOpen}
            onClose={() => setGovOrgModalOpen(false)}
          />
        </>
      )}
    </div>
  );
}

export default DashboardOptionsMenu;
