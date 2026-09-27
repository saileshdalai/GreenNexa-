"use client";

/**
 * GreenNexa — dashboard forecast / trend extras.
 *
 * The Analytics and Command Center styles render a historical trend line and a
 * forecast panel. Both are fetched here, once, for one deterministically chosen
 * metric, and are then shared by every style that needs them. The fetch keys
 * only depend on the organisation and metric, never on the dashboard style, so
 * changing style never triggers a new request.
 */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { pickAnalyticsMetric } from "./dashboardViewModel";

export interface DashboardExtras {
  metric: string | null;
  forecast: { metric: string; unit: string; available: boolean; message: string; points: any[] } | null;
  trend: { metric: string; unit: string; available: boolean; points: any[] } | null;
  loading: boolean;
}

export function useDashboardExtras(orgId: string | null, kpiKeys: string[]): DashboardExtras {
  const metric = pickAnalyticsMetric(kpiKeys);
  const metricKey = metric || "";
  const [extras, setExtras] = useState<DashboardExtras>({
    metric,
    forecast: null,
    trend: null,
    loading: false,
  });

  useEffect(() => {
    if (!orgId || !metricKey) {
      setExtras({ metric: null, forecast: null, trend: null, loading: false });
      return;
    }

    let cancelled = false;
    setExtras((prev) => ({ ...prev, metric: metricKey, loading: true }));

    Promise.allSettled([
      api.get<any>(`/api/v1/forecast/${orgId}`, { sensor_type: metricKey, horizon: "24h" }),
      api.get<any>(`/api/v1/dashboard/${orgId}/timeseries`, { sensor_type: metricKey, period: "24h", limit: 120 }),
    ]).then(([forecastRes, trendRes]) => {
      if (cancelled) return;

      const forecastBody = forecastRes.status === "fulfilled" ? forecastRes.value : null;
      const trendBody = trendRes.status === "fulfilled" ? trendRes.value : null;

      setExtras({
        metric: metricKey,
        forecast: forecastBody
          ? {
              metric: metricKey,
              unit: String(forecastBody.unit ?? ""),
              available: Boolean(forecastBody.is_available) && Array.isArray(forecastBody.forecast) && forecastBody.forecast.length > 0,
              message:
                forecastBody.status_message ||
                "Forecast needs a longer observation window before the model can generate a prediction.",
              points: Array.isArray(forecastBody.forecast) ? forecastBody.forecast : [],
            }
          : null,
        trend: trendBody
          ? {
              metric: metricKey,
              unit: String(trendBody.unit ?? ""),
              available: Array.isArray(trendBody.data) && trendBody.data.length > 1,
              points: Array.isArray(trendBody.data) ? trendBody.data : [],
            }
          : null,
        loading: false,
      });
    });

    return () => {
      cancelled = true;
    };
    // Style is intentionally not a dependency: extras are style-independent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId, metricKey]);

  return extras;
}
