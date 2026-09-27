"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

export interface UnreadNotificationsData {
  has_unread: boolean;
  total_unread: number;
  modules: Record<string, boolean>;
  blocks: Record<string, boolean>;
  wards: Record<string, boolean>;
  module_blocks: Record<string, Record<string, boolean>>;
  sections: Record<string, boolean>;
  unseen_anomaly_ids: string[];
}

export interface MarkReadParams {
  anomaly_ids?: string[];
  metric?: string;
  block_id?: string;
  ward_id?: string;
  all_unseen?: boolean;
  mark_all?: boolean;
}

interface NotificationContextType {
  data: UnreadNotificationsData;
  hasUnread: boolean;
  totalUnread: number;
  isModuleUnread: (moduleKey: string) => boolean;
  isBlockUnread: (blockId: string, moduleKey?: string) => boolean;
  isWardUnread: (wardId: string) => boolean;
  isSectionUnread: (sectionKey: string) => boolean;
  isAnomalyUnseen: (anomalyId: string) => boolean;
  markAsRead: (params: MarkReadParams) => Promise<void>;
  markSingleAnomalyRead: (anomalyId: string) => Promise<void>;
  refreshNotifications: () => Promise<void>;
}

const defaultData: UnreadNotificationsData = {
  has_unread: false,
  total_unread: 0,
  modules: {},
  blocks: {},
  wards: {},
  module_blocks: {},
  sections: {},
  unseen_anomaly_ids: [],
};

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

const CANONICAL_ALIASES: Record<string, string[]> = {
  energy: ["energy", "power", "electricity"],
  water: ["water"],
  waste: ["waste", "waste_level", "waste_weight"],
  air_quality: ["air_quality", "air", "pm25", "pm10"],
  traffic: ["traffic", "traffic_parking"],
  parking: ["parking"],
  assets: ["assets", "asset"],
  safety: ["safety"],
  climate: ["climate", "temperature", "humidity", "co2", "environment", "environmental"],
  street_lighting: ["street_lighting", "street_light"],
  roads: ["roads", "road"],
  parks: ["parks", "park"],
  sewage: ["sewage", "sewage_level", "drainage"],
  water_flow: ["water_flow", "waterflow", "water_level"],
};

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { user, activeOrgId } = useAuth();
  const [data, setData] = useState<UnreadNotificationsData>(defaultData);

  const refreshNotifications = useCallback(async () => {
    if (!user) return;
    try {
      const orgParam = activeOrgId ? `?organisation_id=${encodeURIComponent(activeOrgId)}` : "";
      const res = await api.get<UnreadNotificationsData>(`/api/v1/notifications/unread${orgParam}`);
      if (res) {
        setData({
          has_unread: Boolean(res.has_unread),
          total_unread: Number(res.total_unread || 0),
          modules: res.modules || {},
          blocks: res.blocks || {},
          wards: res.wards || {},
          module_blocks: res.module_blocks || {},
          sections: res.sections || {},
          unseen_anomaly_ids: res.unseen_anomaly_ids || [],
        });
      }
    } catch {
      // Silently catch network errors during polling
    }
  }, [user, activeOrgId]);

  useEffect(() => {
    if (!user) {
      setData(defaultData);
      return;
    }

    refreshNotifications();
    const interval = setInterval(refreshNotifications, 15000); // Check every 15s

    const handleRefresh = () => {
      refreshNotifications();
    };
    window.addEventListener("focus", handleRefresh);
    window.addEventListener("visibilitychange", handleRefresh);
    window.addEventListener("greennexa_demo_mode_changed", handleRefresh);
    window.addEventListener("greennexa_telemetry_updated", handleRefresh);
    window.addEventListener("greennexa_anomaly_updated", handleRefresh);

    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", handleRefresh);
      window.removeEventListener("visibilitychange", handleRefresh);
      window.removeEventListener("greennexa_demo_mode_changed", handleRefresh);
      window.removeEventListener("greennexa_telemetry_updated", handleRefresh);
      window.removeEventListener("greennexa_anomaly_updated", handleRefresh);
    };
  }, [user, activeOrgId, refreshNotifications]);

  const markAsRead = useCallback(
    async (params: MarkReadParams) => {
      try {
        const orgParam = activeOrgId ? `?organisation_id=${encodeURIComponent(activeOrgId)}` : "";
        const payload = activeOrgId ? { organisation_id: activeOrgId, ...params } : params;
        await api.post(`/api/v1/notifications/mark-read${orgParam}`, payload);
        await refreshNotifications();
      } catch (err) {
        console.error("Failed to mark notifications as read:", err);
      }
    },
    [activeOrgId, refreshNotifications]
  );

  const markSingleAnomalyRead = useCallback(
    async (anomalyId: string) => {
      try {
        const orgParam = activeOrgId ? `?organisation_id=${encodeURIComponent(activeOrgId)}` : "";
        await api.post(`/api/v1/notifications/read/${anomalyId}${orgParam}`, {});
        await refreshNotifications();
      } catch (err) {
        console.error("Failed to mark single anomaly as read:", err);
      }
    },
    [activeOrgId, refreshNotifications]
  );

  const isModuleUnread = useCallback(
    (moduleKey: string) => {
      if (!moduleKey || !data.modules) return false;
      const key = moduleKey.toLowerCase().trim();
      if (data.modules[key]) return true;

      // Check direct aliases
      const aliases = CANONICAL_ALIASES[key] || [];
      for (const a of aliases) {
        if (data.modules[a]) return true;
      }

      // Check reverse aliases
      for (const [canonical, group] of Object.entries(CANONICAL_ALIASES)) {
        if (group.includes(key)) {
          if (data.modules[canonical] || group.some((g) => data.modules[g])) {
            return true;
          }
        }
      }

      return false;
    },
    [data.modules]
  );

  const isBlockUnread = useCallback(
    (blockId: string, moduleKey?: string) => {
      if (!blockId) return false;
      const bKey = blockId.trim();
      const bLower = bKey.toLowerCase();

      if (moduleKey) {
        const mKey = moduleKey.toLowerCase().trim();
        const checkModules = [mKey, ...(CANONICAL_ALIASES[mKey] || [])];
        for (const [canonical, group] of Object.entries(CANONICAL_ALIASES)) {
          if (group.includes(mKey) && !checkModules.includes(canonical)) {
            checkModules.push(canonical);
          }
        }

        for (const m of checkModules) {
          const blkMap = data.module_blocks?.[m];
          if (blkMap) {
            if (blkMap[bKey] || blkMap[bLower]) return true;
            for (const [k, v] of Object.entries(blkMap)) {
              if (v && k.toLowerCase() === bLower) return true;
            }
          }
        }
      }

      if (data.blocks?.[bKey] || data.blocks?.[bLower]) return true;
      if (data.blocks) {
        for (const [k, v] of Object.entries(data.blocks)) {
          if (v && k.toLowerCase() === bLower) return true;
        }
      }
      return false;
    },
    [data.blocks, data.module_blocks]
  );

  const isWardUnread = useCallback(
    (wardId: string) => {
      if (!wardId || !data.wards) return false;
      const wKey = String(wardId).trim();
      const wLower = wKey.toLowerCase();
      if (data.wards[wKey] || data.wards[wLower]) return true;
      for (const [k, v] of Object.entries(data.wards)) {
        if (v && (k === wKey || k.toLowerCase() === wLower)) return true;
      }
      return false;
    },
    [data.wards]
  );

  const isSectionUnread = useCallback(
    (sectionKey: string) => {
      if (!sectionKey) return false;
      const sKey = sectionKey.toLowerCase().trim();
      if (sKey === "anomalies") {
        return Boolean(
          data.sections?.anomalies ||
            data.has_unread ||
            (data.unseen_anomaly_ids && data.unseen_anomaly_ids.length > 0)
        );
      }
      return Boolean(data.sections?.[sKey]);
    },
    [data.sections, data.has_unread, data.unseen_anomaly_ids]
  );

  const isAnomalyUnseen = useCallback(
    (anomalyId: string) => {
      if (!anomalyId || !data.unseen_anomaly_ids) return false;
      return data.unseen_anomaly_ids.includes(anomalyId);
    },
    [data.unseen_anomaly_ids]
  );

  return (
    <NotificationContext.Provider
      value={{
        data,
        hasUnread: data.has_unread,
        totalUnread: data.total_unread,
        isModuleUnread,
        isBlockUnread,
        isWardUnread,
        isSectionUnread,
        isAnomalyUnseen,
        markAsRead,
        markSingleAnomalyRead,
        refreshNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

const fallbackContext: NotificationContextType = {
  data: defaultData,
  hasUnread: false,
  totalUnread: 0,
  isModuleUnread: () => false,
  isBlockUnread: () => false,
  isWardUnread: () => false,
  isSectionUnread: () => false,
  isAnomalyUnseen: () => false,
  markAsRead: async () => {},
  markSingleAnomalyRead: async () => {},
  refreshNotifications: async () => {},
};

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    return fallbackContext;
  }
  return context;
}
