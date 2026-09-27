"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, Organisation, OrganisationListResponse, AuthResponse } from "@/types";
import { api } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  activeOrgId: string | null;
  currentOrg: Organisation | null;
  organisations: Organisation[];
  enabledModules: string[] | null;
  login: (email: string, pass: string, organisationType?: string) => Promise<User>;
  logout: () => void;
  setActiveOrgId: (orgId: string) => void;
  refreshUser: () => Promise<void>;
  refreshSensorConfig: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeOrgId, setActiveOrgIdState] = useState<string | null>(null);
  const [currentOrg, setCurrentOrg] = useState<Organisation | null>(null);
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [enabledModules, setEnabledModules] = useState<string[] | null>(null);

  const fetchOrganisations = async (): Promise<Organisation[]> => {
    try {
      const data = await api.get<OrganisationListResponse | Organisation[]>("/api/v1/organisations");
      const list = Array.isArray(data) ? data : data?.items || [];
      setOrganisations(list);
      return list;
    } catch {
      return [];
    }
  };

  const fetchSensorConfig = async () => {
    try {
      const data = await api.get<{ enabled_modules?: string[]; enabled_sensors?: string[] }>("/api/v1/organisation/sensor-config");
      const modules = data.enabled_modules || data.enabled_sensors || null;
      setEnabledModules(modules);
    } catch {
      setEnabledModules(null);
    }
  };

  const refreshUser = async () => {
    const savedToken = localStorage.getItem("greennexa_token");
    if (!savedToken) {
      setUser(null);
      setToken(null);
      setEnabledModules(null);
      setLoading(false);
      return;
    }

    try {
      setToken(savedToken);
      const userData = await api.get<User>("/api/v1/auth/me");
      setUser(userData);
      
      const savedOrg = localStorage.getItem("greennexa_active_org");
      if (userData.role === "SUPER_ADMIN") {
        const orgList = await fetchOrganisations();
        const initialOrg = savedOrg || userData.organisation_id || (orgList.length > 0 ? orgList[0].id : null);
        if (initialOrg) {
          setActiveOrgIdState(initialOrg);
          localStorage.setItem("greennexa_active_org", initialOrg);
        }
      } else {
        const adminOrg = userData.organisation_id || null;
        setActiveOrgIdState(adminOrg);
        if (adminOrg) {
          localStorage.setItem("greennexa_active_org", adminOrg);
        }
      }

      await fetchSensorConfig();
    } catch {
      localStorage.removeItem("greennexa_token");
      setUser(null);
      setToken(null);
      setActiveOrgIdState(null);
      setEnabledModules(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, pass: string, organisationType?: string): Promise<User> => {
    const payload: { email: string; password: string; organisation_type?: string } = {
      email,
      password: pass,
    };
    if (organisationType) {
      payload.organisation_type = organisationType;
    }
    const data = await api.post<AuthResponse>("/api/v1/auth/login", payload);
    localStorage.setItem("greennexa_token", data.access_token);
    setToken(data.access_token);
    setUser(data.user);

    if (data.user.role === "SUPER_ADMIN") {
      const orgList = await fetchOrganisations();
      const savedOrg = localStorage.getItem("greennexa_active_org");
      const firstOrg = savedOrg || data.user.organisation_id || (orgList.length > 0 ? orgList[0].id : null);
      if (firstOrg) {
        setActiveOrgIdState(firstOrg);
        localStorage.setItem("greennexa_active_org", firstOrg);
      }
    } else {
      const adminOrg = data.user.organisation_id || null;
      setActiveOrgIdState(adminOrg);
      if (adminOrg) {
        localStorage.setItem("greennexa_active_org", adminOrg);
      }
    }

    if (typeof window !== "undefined") {
      localStorage.removeItem("greennexa_demo_mode");
      localStorage.removeItem("greennexa_sim_cycle_start_ms");
      localStorage.removeItem("greennexa_active_demo_modules");
      localStorage.removeItem("greennexa_demo_scope");
    }

    await fetchSensorConfig();
    return data.user;
  };

  const logout = () => {
    const org = activeOrgId || (typeof window !== "undefined" ? localStorage.getItem("greennexa_active_org") : null);
    if (token) {
      const logoutUrl = org ? `/api/v1/auth/logout?organisation_id=${encodeURIComponent(org)}` : "/api/v1/auth/logout";
      api.post(logoutUrl, {}).catch(() => {});
      api.post("/api/v1/simulator/synthetic/stop", org ? { organisation_id: org } : {}).catch(() => {});
    }

    if (typeof window !== "undefined") {
      localStorage.removeItem("greennexa_token");
      localStorage.removeItem("greennexa_active_org");
      localStorage.removeItem("greennexa_demo_mode");
      localStorage.removeItem("greennexa_sim_cycle_start_ms");
      localStorage.removeItem("greennexa_active_demo_modules");
      localStorage.removeItem("greennexa_demo_scope");
      window.dispatchEvent(new CustomEvent("greennexa_demo_mode_changed", { detail: { active: false } }));
    }

    setUser(null);
    setToken(null);
    setActiveOrgIdState(null);
    setEnabledModules(null);
  };

  const setActiveOrgId = (orgId: string) => {
    setActiveOrgIdState(orgId);
    localStorage.setItem("greennexa_active_org", orgId);
    fetchSensorConfig();
  };

  useEffect(() => {
    if (!activeOrgId) {
      setCurrentOrg(null);
      return;
    }
    const found = organisations.find((o) => o.id === activeOrgId);
    if (found) {
      setCurrentOrg(found);
    } else {
      api.get<Organisation>(`/api/v1/organisations/${activeOrgId}`)
        .then((org) => setCurrentOrg(org))
        .catch(() => setCurrentOrg(null));
    }
  }, [activeOrgId, organisations]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        activeOrgId,
        currentOrg,
        organisations,
        enabledModules,
        login,
        logout,
        setActiveOrgId,
        refreshUser,
        refreshSensorConfig: fetchSensorConfig,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
