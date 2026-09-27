"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

export function formatSimDate(dateStr: string, dayOfWeek?: string): string {
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const monthIdx = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const dateObj = new Date(Date.UTC(year, monthIdx, day));
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
      const dayName = dayOfWeek || days[dateObj.getUTCDay()];
      return `${day} ${months[monthIdx]} ${year} / ${dayName}`;
    }
  } catch {
    // fallback
  }
  return `${dateStr} / ${dayOfWeek || "SUN"}`;
}

export function calculateWeekday(dateStr: string): string {
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const monthIdx = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const dateObj = new Date(Date.UTC(year, monthIdx, day));
      const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
      return days[dateObj.getUTCDay()];
    }
  } catch {
    // fallback
  }
  return "MON";
}

export function getCurrentModuleFromPath(pathname: string): string | null {
  if (!pathname) return null;
  const clean = pathname.toLowerCase();
  const moduleMatch = clean.match(/\/dashboard\/modules\/([a-z0-9_-]+)/);
  if (moduleMatch && moduleMatch[1]) {
    return moduleMatch[1];
  }
  if (clean.includes("/energy")) return "energy";
  if (clean.includes("/water")) return "water";
  if (clean.includes("/waste")) return "waste";
  if (clean.includes("/air_quality") || clean.includes("/air-quality")) return "air_quality";
  if (clean.includes("/traffic")) return "traffic";
  if (clean.includes("/parking")) return "parking";
  if (clean.includes("/assets") || clean.includes("/asset")) return "assets";
  if (clean.includes("/safety")) return "safety";
  if (clean.includes("/climate") || clean.includes("/environment")) return "climate";
  if (clean.includes("/street_lighting") || clean.includes("/street-lighting")) return "street_lighting";
  if (clean.includes("/roads") || clean.includes("/road")) return "roads";
  if (clean.includes("/parks") || clean.includes("/park")) return "parks";
  if (clean.includes("/sewage") || clean.includes("/drainage")) return "sewage";
  return null;
}

interface DemoContextType {
  demoModeActive: boolean;
  activeDemoModules: string[];
  isModuleInDemo: (modName: string) => boolean;
  presentationModeActive: boolean;
  walkthroughOpen: boolean;
  currentWalkthroughStep: number;
  simulatedDate: string;
  simulatedDayName: string;
  formattedDate: string;
  isChangingDay: boolean;
  /** 0–29: seconds elapsed within the current 30-second simulator cycle. Persists across route changes. */
  simElapsedSeconds: number;
  toggleDemoMode: (targetModule?: string) => Promise<void>;
  togglePresentationMode: () => void;
  startWalkthrough: () => void;
  stopWalkthrough: () => void;
  nextWalkthroughStep: () => void;
  prevWalkthroughStep: () => void;
  setWalkthroughStep: (step: number) => void;
  changeSimulatedDay: (days?: number, targetOrg?: string | null) => Promise<void>;
  setSimulatedDateDirect: (newDate: string, targetOrg?: string | null) => Promise<void>;
  refreshSimulatedDay: (targetOrg?: string | null) => Promise<void>;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);

export const DemoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, user } = useAuth();
  const [demoModeActive, setDemoModeActive] = useState<boolean>(false);
  const [activeDemoModules, setActiveDemoModules] = useState<string[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const raw = localStorage.getItem("greennexa_active_demo_modules");
        return raw ? JSON.parse(raw) : [];
      } catch {
        return [];
      }
    }
    return [];
  });
  const [presentationModeActive, setPresentationModeActive] = useState<boolean>(false);
  const [walkthroughOpen, setWalkthroughOpen] = useState<boolean>(false);
  const [currentWalkthroughStep, setCurrentWalkthroughStep] = useState<number>(1);

  const isModuleInDemo = (modName: string): boolean => {
    if (!demoModeActive) return false;
    if (!activeDemoModules || activeDemoModules.length === 0) return true;
    const clean = (modName || "").toLowerCase().trim();
    return activeDemoModules.includes(clean);
  };

  const [simulatedDate, setSimulatedDate] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("greennexa_simulated_date") || "2026-09-20";
    }
    return "2026-09-20";
  });

  const [simulatedDayName, setSimulatedDayName] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("greennexa_simulated_day_name") || "SUN";
    }
    return "SUN";
  });

  const [formattedDate, setFormattedDate] = useState<string>(() => {
    if (typeof window !== "undefined") {
      const d = localStorage.getItem("greennexa_simulated_date") || "2026-09-20";
      const day = localStorage.getItem("greennexa_simulated_day_name") || "SUN";
      return formatSimDate(d, day);
    }
    return "20 Sep 2026 / SUN";
  });

  const [isChangingDay, setIsChangingDay] = useState<boolean>(false);

  // ---- Simulator 30-second cycle progress (global, persists across route changes) ----
  const [simElapsedSeconds, setSimElapsedSeconds] = useState<number>(() => {
    if (typeof window !== "undefined") {
      const startMs = localStorage.getItem("greennexa_sim_cycle_start_ms");
      if (startMs) {
        const elapsed = Math.floor((Date.now() - parseInt(startMs, 10)) / 1000) % 30;
        return Math.max(0, elapsed);
      }
    }
    return 0;
  });

  const syncSimulatorStatus = async () => {
    try {
      const effectiveOrg = getEffectiveOrg();
      const status = await api.get<{
        running: boolean;
        demo_mode?: boolean;
        generation_active?: boolean;
        active_modules?: string[];
      }>(
        "/api/v1/simulator/synthetic/status",
        effectiveOrg ? { organisation_id: effectiveOrg } : undefined
      );
      // demo_mode reflects the PER-ORG demo enrollment so scope isolation is
      // respected in the UI (an org outside the demo scope is NOT "in demo").
      const active = Boolean(status.demo_mode ?? status.running);
      setDemoModeActive(active);
      const mods = status.active_modules || [];
      setActiveDemoModules(mods);
      if (typeof window !== "undefined") {
        localStorage.setItem("greennexa_demo_mode", String(active));
        localStorage.setItem("greennexa_active_demo_modules", JSON.stringify(mods));
      }
    } catch {
      const savedDemo = typeof window !== "undefined" ? localStorage.getItem("greennexa_demo_mode") : null;
      if (savedDemo !== null) {
        setDemoModeActive(savedDemo === "true");
      }
    }
  };

  const getEffectiveOrg = (targetOrg?: string | null): string | undefined => {
    let org = targetOrg;
    if (!org && typeof window !== "undefined") {
      org = localStorage.getItem("greennexa_active_org") || localStorage.getItem("greennexa_active_org_id");
    }
    if (!org || org === "null" || org === "undefined" || org.trim() === "") {
      return undefined;
    }
    return org.trim();
  };

  const refreshSimulatedDay = async (targetOrg?: string | null) => {
    try {
      const effectiveOrg = getEffectiveOrg(targetOrg);
      const res = await api.get<{
        simulated_date: string;
        day_of_week: string;
        day_name: string;
        is_simulated: boolean;
      }>("/api/v1/simulator/synthetic/current-day", effectiveOrg ? { organisation_id: effectiveOrg } : undefined);
      if (res && res.simulated_date) {
        setSimulatedDate(res.simulated_date);
        setSimulatedDayName(res.day_of_week || "SUN");
        setFormattedDate(formatSimDate(res.simulated_date, res.day_of_week));
        if (typeof window !== "undefined") {
          localStorage.setItem("greennexa_simulated_date", res.simulated_date);
          localStorage.setItem("greennexa_simulated_day_name", res.day_of_week || "SUN");
        }
      }
    } catch {
      // ignore
    }
  };

  const changeSimulatedDay = async (days: number = 1, targetOrg?: string | null) => {
    setIsChangingDay(true);
    try {
      const effectiveOrg = getEffectiveOrg(targetOrg);
      const res = await api.post<{
        status: string;
        simulated_date: string;
        day_of_week: string;
        day_name: string;
        message: string;
      }>("/api/v1/simulator/synthetic/change-day", {
        days,
        organisation_id: effectiveOrg,
      });
      if (res && res.simulated_date) {
        setSimulatedDate(res.simulated_date);
        setSimulatedDayName(res.day_of_week || "SUN");
        setFormattedDate(formatSimDate(res.simulated_date, res.day_of_week));
        if (typeof window !== "undefined") {
          localStorage.setItem("greennexa_simulated_date", res.simulated_date);
          localStorage.setItem("greennexa_simulated_day_name", res.day_of_week || "SUN");
          window.dispatchEvent(new CustomEvent("greennexa_day_changed", { detail: res }));
          window.dispatchEvent(new CustomEvent("greennexa_telemetry_updated"));
        }
      }
    } catch (err) {
      console.error("Failed to change simulated day:", err);
    } finally {
      setIsChangingDay(false);
    }
  };

  const setSimulatedDateDirect = async (newDate: string, targetOrg?: string | null) => {
    setIsChangingDay(true);
    try {
      const effectiveOrg = getEffectiveOrg(targetOrg);
      const res = await api.post<{
        status: string;
        simulated_date: string;
        day_of_week: string;
        day_name: string;
        message: string;
      }>("/api/v1/simulator/synthetic/set-date", {
        date: newDate,
        organisation_id: effectiveOrg,
      });
      if (res && res.simulated_date) {
        setSimulatedDate(res.simulated_date);
        setSimulatedDayName(res.day_of_week || "SUN");
        setFormattedDate(formatSimDate(res.simulated_date, res.day_of_week));
        if (typeof window !== "undefined") {
          localStorage.setItem("greennexa_simulated_date", res.simulated_date);
          localStorage.setItem("greennexa_simulated_day_name", res.day_of_week || "SUN");
          window.dispatchEvent(new CustomEvent("greennexa_day_changed", { detail: res }));
          window.dispatchEvent(new CustomEvent("greennexa_telemetry_updated"));
        }
      }
    } catch (err) {
      console.error("Failed to manually set simulated date:", err);
      throw err;
    } finally {
      setIsChangingDay(false);
    }
  };

  useEffect(() => {
    if (!user || !token) {
      setDemoModeActive(false);
      setActiveDemoModules([]);
      setSimElapsedSeconds(0);
      if (typeof window !== "undefined") {
        localStorage.removeItem("greennexa_demo_mode");
        localStorage.removeItem("greennexa_sim_cycle_start_ms");
        localStorage.removeItem("greennexa_active_demo_modules");
      }
      return;
    }

    syncSimulatorStatus();
    refreshSimulatedDay();
    const interval = setInterval(() => {
      syncSimulatorStatus();
      refreshSimulatedDay();
    }, 15000);
    return () => clearInterval(interval);
  }, [token, user]);

  useEffect(() => {
    const handleDemoChange = (e: any) => {
      if (e?.detail && e.detail.active === false) {
        setDemoModeActive(false);
        setActiveDemoModules([]);
        setSimElapsedSeconds(0);
      }
    };
    window.addEventListener("greennexa_demo_mode_changed", handleDemoChange);
    return () => window.removeEventListener("greennexa_demo_mode_changed", handleDemoChange);
  }, []);

  // ---- Global 1-second tick for simulator cycle progress bar ----
  useEffect(() => {
    const tick = setInterval(() => {
      if (typeof window !== "undefined") {
        let startMs = localStorage.getItem("greennexa_sim_cycle_start_ms");
        if (!startMs && demoModeActive) {
          startMs = String(Date.now());
          localStorage.setItem("greennexa_sim_cycle_start_ms", startMs);
        }
        if (startMs && demoModeActive) {
          const elapsed = Math.floor((Date.now() - parseInt(startMs, 10)) / 1000) % 30;
          setSimElapsedSeconds(Math.max(0, elapsed));
        } else {
          setSimElapsedSeconds(0);
        }
      }
    }, 1000);
    return () => clearInterval(tick);
  }, [demoModeActive]);

  const toggleDemoMode = async (targetModule?: string) => {
    const next = !demoModeActive;
    try {
      const effectiveOrg = getEffectiveOrg();
      const currentModule = targetModule || (typeof window !== "undefined" ? getCurrentModuleFromPath(window.location.pathname) : null);
      if (next) {
        const payload: any = {
          interval_seconds: 30,
          demo_mode: true,
          ...(effectiveOrg ? { organisation_id: effectiveOrg } : {}),
          ...(currentModule ? { module: currentModule } : {}),
        };
        const startUrl = `/api/v1/simulator/synthetic/start${currentModule ? `?module=${encodeURIComponent(currentModule)}` : ""}`;
        const res = await api.post<{ running: boolean; demo_mode?: boolean; active_modules?: string[] }>(
          startUrl,
          payload
        );
        const isActive = res.demo_mode ?? res.running ?? true;
        setDemoModeActive(isActive);
        const mods = res.active_modules || (currentModule ? [currentModule] : []);
        setActiveDemoModules(mods);
        if (typeof window !== "undefined") {
          localStorage.setItem("greennexa_demo_mode", String(isActive));
          localStorage.setItem("greennexa_active_demo_modules", JSON.stringify(mods));
          const nowMs = String(Date.now());
          localStorage.setItem("greennexa_sim_cycle_start_ms", nowMs);
        }
        setSimElapsedSeconds(0);
      } else {
        const stopUrl = `/api/v1/simulator/synthetic/stop${currentModule ? `?module=${encodeURIComponent(currentModule)}` : ""}`;
        const res = await api.post<{ running: boolean; demo_mode?: boolean; active_modules?: string[] }>(
          stopUrl,
          effectiveOrg ? { organisation_id: effectiveOrg } : {}
        );
        const isActive = res.demo_mode ?? res.running ?? false;
        setDemoModeActive(isActive);
        const mods = res.active_modules || [];
        setActiveDemoModules(mods);
        if (typeof window !== "undefined") {
          localStorage.setItem("greennexa_demo_mode", String(isActive));
          localStorage.setItem("greennexa_active_demo_modules", JSON.stringify(mods));
          if (!isActive) {
            localStorage.removeItem("greennexa_sim_cycle_start_ms");
          }
        }
        if (!isActive) {
          setSimElapsedSeconds(0);
        }
      }
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("greennexa_demo_mode_changed", {
            detail: { active: next, organisation_id: effectiveOrg, module: currentModule },
          })
        );
      }
    } catch (err) {
      console.error("Failed to toggle demo mode:", err);
    }
  };

  const togglePresentationMode = () => {
    setPresentationModeActive((prev) => !prev);
  };

  const startWalkthrough = () => {
    setCurrentWalkthroughStep(1);
    setWalkthroughOpen(true);
  };

  const stopWalkthrough = () => {
    setWalkthroughOpen(false);
  };

  const nextWalkthroughStep = () => {
    setCurrentWalkthroughStep((prev) => Math.min(prev + 1, 7));
  };

  const prevWalkthroughStep = () => {
    setCurrentWalkthroughStep((prev) => Math.max(prev - 1, 1));
  };

  const setWalkthroughStep = (step: number) => {
    if (step >= 1 && step <= 7) {
      setCurrentWalkthroughStep(step);
    }
  };

  return (
    <DemoContext.Provider
      value={{
        demoModeActive,
        activeDemoModules,
        isModuleInDemo,
        presentationModeActive,
        walkthroughOpen,
        currentWalkthroughStep,
        simulatedDate,
        simulatedDayName,
        formattedDate,
        isChangingDay,
        simElapsedSeconds,
        toggleDemoMode,
        togglePresentationMode,
        startWalkthrough,
        stopWalkthrough,
        nextWalkthroughStep,
        prevWalkthroughStep,
        setWalkthroughStep,
        changeSimulatedDay,
        setSimulatedDateDirect,
        refreshSimulatedDay,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
};

export const useDemo = () => {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error("useDemo must be used within a DemoProvider");
  }
  return context;
};
