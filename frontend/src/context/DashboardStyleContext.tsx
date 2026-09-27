"use client";

/**
 * GreenNexa — Dashboard Style Context.
 *
 * Owns the per-organisation dashboard presentation style. The style is a pure
 * presentation preference: changing it never refetches, mutates, resets or
 * restarts telemetry, anomalies, forecasts, recommendations, Demo Mode, the
 * simulator, IoT mode or any module. The server (`Organisation.dashboard_style`)
 * is the source of truth; localStorage is only a paint cache so that switching
 * organisation or reloading does not flash the wrong layout.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  DEFAULT_DASHBOARD_STYLE,
  DASHBOARD_STYLES,
  DashboardStyle,
  DashboardStyleDefinition,
  cacheDashboardStyle,
  readCachedDashboardStyle,
  normaliseDashboardStyle,
} from "@/lib/dashboardStyles";

interface DashboardStyleContextValue {
  /** Style currently applied to the active organisation dashboard. */
  style: DashboardStyle;
  /** Registry entries for the four styles. */
  styles: DashboardStyleDefinition[];
  /** Currently selected definition. */
  definition: DashboardStyleDefinition;
  /** True when the style has not yet been confirmed by the server. */
  loading: boolean;
  /** True while a style change is being persisted. */
  saving: boolean;
  /** Last persistence error (already human readable) or null. */
  error: string | null;
  /** Persist a new style for the active organisation. */
  setStyle: (next: DashboardStyle) => Promise<void>;
  /** Organisation the current style belongs to. */
  organisationId: string | null;
}

const DashboardStyleContext = createContext<DashboardStyleContextValue | null>(null);

function readCache(organisationId: string): DashboardStyle | null {
  if (typeof window === "undefined" || !organisationId) return null;
  return readCachedDashboardStyle(window.localStorage, organisationId);
}

function writeCache(organisationId: string, style: DashboardStyle) {
  if (typeof window === "undefined" || !organisationId) return;
  cacheDashboardStyle(window.localStorage, organisationId, style);
}

export function DashboardStyleProvider({ children }: { children: React.ReactNode }) {
  const { user, activeOrgId, currentOrg } = useAuth();
  const organisationId = currentOrg?.id || activeOrgId || user?.organisation_id || null;

  const [styleByOrg, setStyleByOrg] = useState<Record<string, DashboardStyle>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestedOrgRef = useRef<string | null>(null);

  const readStyle = useCallback(
    (orgId: string) => {
      const cached = readCache(orgId);
      setStyleByOrg((prev) => (cached && !prev[orgId] ? { ...prev, [orgId]: cached } : prev));
      return cached;
    },
    []
  );

  // Confirm the style for the active organisation with the server.
  useEffect(() => {
    if (!organisationId) return;
    requestedOrgRef.current = organisationId;
    readStyle(organisationId);
    setLoading(true);
    setError(null);

    let cancelled = false;
    api
      .get<{ dashboard_style?: string; organisation_id?: string }>(`/api/v1/dashboard/${organisationId}/style`)
      .then((res) => {
        if (cancelled || requestedOrgRef.current !== organisationId) return;
        const remote = normaliseDashboardStyle(res?.dashboard_style);
        setStyleByOrg((prev) => ({ ...prev, [organisationId]: remote }));
        writeCache(organisationId, remote);
      })
      .catch((err: any) => {
        if (cancelled || requestedOrgRef.current !== organisationId) return;
        // A missing/denied style endpoint must never break the dashboard:
        // fall back to the cached value or the default presentation.
        setStyleByOrg((prev) => (prev[organisationId] ? prev : { ...prev, [organisationId]: DEFAULT_DASHBOARD_STYLE }));
        if (err?.status && err.status !== 403 && err.status !== 404) {
          setError("Dashboard style could not be confirmed — showing the default layout.");
        }
      })
      .finally(() => {
        if (!cancelled && requestedOrgRef.current === organisationId) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [organisationId, readStyle]);

  const setStyle = useCallback(
    async (next: DashboardStyle) => {
      const normalised = normaliseDashboardStyle(next);
      if (!organisationId) return;
      const previous = styleByOrg[organisationId] ?? DEFAULT_DASHBOARD_STYLE;
      if (normalised === previous) return;

      // Optimistic, presentation-only update: the layout changes immediately and
      // no dashboard data request is triggered.
      setError(null);
      setSaving(true);
      setStyleByOrg((prev) => ({ ...prev, [organisationId]: normalised }));
      writeCache(organisationId, normalised);

      try {
        const res = await api.put<{ dashboard_style?: string }>(`/api/v1/dashboard/${organisationId}/style`, {
          dashboard_style: normalised,
        });
        const confirmed = normaliseDashboardStyle(res?.dashboard_style ?? normalised);
        setStyleByOrg((prev) => ({ ...prev, [organisationId]: confirmed }));
        writeCache(organisationId, confirmed);
      } catch (err: any) {
        // Revert the presentation-only change; no data is touched either way.
        setStyleByOrg((prev) => ({ ...prev, [organisationId]: previous }));
        writeCache(organisationId, previous);
        setError(
          err?.status === 403
            ? "You do not have permission to change this dashboard style."
            : "Could not save the dashboard style — the previous layout was restored."
        );
      } finally {
        setSaving(false);
      }
    },
    [organisationId, styleByOrg]
  );

  const style = (organisationId && styleByOrg[organisationId]) || DEFAULT_DASHBOARD_STYLE;
  const definition = DASHBOARD_STYLES.find((s) => s.id === style) ?? DASHBOARD_STYLES[0];

  const value = useMemo<DashboardStyleContextValue>(
    () => ({ style, styles: DASHBOARD_STYLES, definition, loading, saving, error, setStyle, organisationId }),
    [style, definition, loading, saving, error, setStyle, organisationId]
  );

  return <DashboardStyleContext.Provider value={value}>{children}</DashboardStyleContext.Provider>;
}

export function useDashboardStyle(): DashboardStyleContextValue {
  const ctx = useContext(DashboardStyleContext);
  if (ctx) return ctx;
  // Safe fallback so pages rendered outside the provider still work.
  return {
    style: DEFAULT_DASHBOARD_STYLE,
    styles: DASHBOARD_STYLES,
    definition: DASHBOARD_STYLES[0],
    loading: false,
    saving: false,
    error: null,
    setStyle: async () => {},
    organisationId: null,
  };
}
