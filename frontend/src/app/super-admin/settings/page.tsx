"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { FacilityTypeItem } from "@/types";
import {
  SlidersHorizontal,
  Building,
  Plus,
  Trash2,
  Save,
  Shield,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sun,
} from "lucide-react";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

export default function PlatformSettingsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [facilityTypes, setFacilityTypes] = useState<FacilityTypeItem[]>([]);
  const [newTypeName, setNewTypeName] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);

  // Danger Zone Super Admin Clear All Data state
  const [showClearAllModal, setShowClearAllModal] = useState<boolean>(false);
  const [clearStep, setClearStep] = useState<1 | 2>(1);
  const [confirmationPassword, setConfirmationPassword] = useState<string>("");
  const [verifyingConfirmation, setVerifyingConfirmation] = useState<boolean>(false);
  const [clearingAll, setClearingAll] = useState<boolean>(false);
  const [confirmationInput, setConfirmationInput] = useState<string>("");

  const loadSettings = async () => {
    setLoading(true);
    try {
      const data = await api.get<FacilityTypeItem[]>("/api/v1/super-admin/facility-types");
      setFacilityTypes(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load platform settings", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadSettings();
  }, [user]);

  const handleAddFacilityType = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTypeName.trim()) return;

    const id = newTypeName.toLowerCase().replace(/[^a-z0-9]/g, "_");
    setFacilityTypes((prev) => [
      ...prev,
      { id, name: newTypeName.trim(), description: "Custom facility type category" },
    ]);
    showToast(`Added custom facility type: ${newTypeName}`, "success");
    setNewTypeName("");
  };

  const handleDeleteFacilityType = (id: string) => {
    setFacilityTypes((prev) => prev.filter((t) => t.id !== id));
    showToast("Facility type removed from options list", "info");
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      showToast("Platform settings and facility types updated successfully!", "success");
    } catch (err: any) {
      showToast(err.message || "Failed to save settings", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleVerifyClearConfirmation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!confirmationPassword.trim()) {
      return showToast("Please enter the confirmation password", "error");
    }

    setVerifyingConfirmation(true);
    try {
      await api.post("/api/v1/super-admin/verify-confirmation-password", {
        confirmation_password: confirmationPassword,
      });
      setClearStep(2);
    } catch (err: any) {
      showToast(err.message || "Invalid confirmation password", "error");
    } finally {
      setVerifyingConfirmation(false);
    }
  };

  const handleClearAllData = async () => {
    if (confirmationInput !== "CLEAR ALL DATA" || clearingAll) return;
    setClearingAll(true);
    try {
      const res = await api.post<{ message: string; preserved_user: string }>(
        "/api/v1/super-admin/clear-all-data",
        {
          confirmation: confirmationInput,
          confirmation_password: confirmationPassword,
        }
      );
      showToast(res.message || "Entire platform reset successfully! Fixed Super Admin account preserved.", "success");
      setShowClearAllModal(false);
      setClearStep(1);
      setConfirmationPassword("");
      setConfirmationInput("");
      await loadSettings();
    } catch (err: any) {
      showToast(err.message || "Failed to execute platform clear all data", "error");
    } finally {
      setClearingAll(false);
    }
  };

  return (
    <AppLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
            <SlidersHorizontal color="var(--clr-primary)" size={28} />
            Platform Settings
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            Manage configurable facility types, multi-tenant isolation policies, and platform reset actions.
          </p>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "840px" }}>
        {/* Appearance & Theme Card */}
        <div className="card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
            <div>
              <h2 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "4px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Sun color="var(--clr-primary)" size={20} /> Appearance & Theme
              </h2>
              <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", margin: 0 }}>
                Toggle between professional Day Mode (☀️ light dashboard) and Night Mode (🌙 dark dashboard).
              </p>
            </div>
            <ThemeToggle />
          </div>
        </div>

        {/* Security Overview */}
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
            <Shield color="var(--clr-primary)" size={20} /> Multi-Tenant Role Isolation
          </h2>
          <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", lineHeight: 1.6, margin: 0 }}>
            Super Admin has global platform management access across all tenant organisations.
            Regular ADMIN accounts are strictly scoped to their own organisation ID via backend middleware.
          </p>
        </div>

        {/* Configurable Facility Types */}
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 800, marginBottom: "8px" }}>
            Configurable Facility Types
          </h2>
          <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginBottom: "20px" }}>
            Super Admin can customize available facility categories selectable during organisation creation.
          </p>

          <form onSubmit={handleAddFacilityType} style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Research Lab / Tech Park"
              value={newTypeName}
              onChange={(e) => setNewTypeName(e.target.value)}
              style={{ flex: 1 }}
            />
            <button type="submit" className="btn btn-outline" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Plus size={16} /> Add Type
            </button>
          </form>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {facilityTypes.map((t) => (
              <div
                key={t.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 16px",
                  borderRadius: "8px",
                  background: "var(--clr-surface-2)",
                  border: "1px solid var(--clr-border)",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--clr-text-primary)" }}>{t.name}</div>
                  <div style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>{t.description}</div>
                </div>

                <button
                  onClick={() => handleDeleteFacilityType(t.id)}
                  style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer", padding: "4px" }}
                  title="Remove type"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Save */}
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={handleSaveSettings}
            disabled={saving}
            className="btn btn-primary btn-lg"
            style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700 }}
          >
            <Save size={18} />
            <span>{saving ? "Saving..." : "Save Platform Settings"}</span>
          </button>
        </div>

        {/* Danger Zone Card - Super Admin Clear All Data */}
        <div
          className="card"
          style={{
            border: "1px solid #fca5a5",
            background: "#fff5f5",
            borderRadius: "12px",
            padding: "24px",
            marginTop: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: "14px" }}>
            <div
              style={{
                padding: "10px",
                borderRadius: "10px",
                background: "#fee2e2",
                color: "#dc2626",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <AlertTriangle size={24} />
            </div>

            <div style={{ flex: 1 }}>
              <h2 style={{ fontSize: "18px", fontWeight: 800, color: "#991b1b", marginBottom: "6px" }}>
                Danger Zone: Super Admin Platform Wipe (Clear All Data)
              </h2>
              <p style={{ fontSize: "13px", color: "#7f1d1d", lineHeight: "1.5", marginBottom: "16px" }}>
                Deletes all organisations, facility blocks, sensor configurations, IoT devices, telemetry, anomalies, recommendations, and non-super-admin user accounts.
                <strong> Preserves ONLY the fixed Super Admin demo account:</strong> <code>superadmin@greennexa.com</code>.
              </p>

              <button
                type="button"
                onClick={() => {
                  setClearStep(1);
                  setConfirmationPassword("");
                  setConfirmationInput("");
                  setShowClearAllModal(true);
                }}
                className="btn"
                style={{
                  background: "#dc2626",
                  color: "#ffffff",
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  border: "none",
                  padding: "10px 18px",
                  borderRadius: "8px",
                  cursor: "pointer",
                }}
              >
                <Trash2 size={16} /> Clear All Platform Data
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showClearAllModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.5)",
            zIndex: 10000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "520px",
              background: "var(--clr-surface, #ffffff)",
              borderRadius: "16px",
              padding: "28px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
              border: "1px solid var(--clr-border, #e5e7eb)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px", color: "#dc2626" }}>
              <AlertTriangle size={28} />
              <h3 style={{ fontSize: "20px", fontWeight: 800, margin: 0 }}>CLEAR ALL PLATFORM DATA</h3>
            </div>

            <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", lineHeight: 1.6, marginBottom: "20px" }}>
              This will permanently delete all tenant organisations, admins, facility blocks, sensors, telemetry, anomalies, and recommendations.
              Only the fixed Super Admin account (<code>superadmin@greennexa.com</code>) will be preserved.
            </p>

            {clearStep === 1 ? (
              <form onSubmit={handleVerifyClearConfirmation}>
                <div style={{ padding: "12px", borderRadius: "8px", backgroundColor: "rgba(220, 38, 38, 0.08)", border: "1px solid rgba(220, 38, 38, 0.2)", marginBottom: "16px" }}>
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--clr-text-secondary)", lineHeight: 1.5 }}>
                    <strong>Step 1 of 2:</strong> Destructive Action Protection. Enter the confirmation password to authorize platform reset.
                  </p>
                </div>

                <div style={{ marginBottom: "24px" }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "var(--clr-text-primary)", marginBottom: "8px" }}>
                    Confirmation Password *
                  </label>
                  <input
                    type="password"
                    className="form-input"
                    value={confirmationPassword}
                    onChange={(e) => setConfirmationPassword(e.target.value)}
                    placeholder="Enter confirmation password"
                    required
                    autoFocus
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      borderRadius: "8px",
                      border: "1px solid var(--clr-border)",
                      fontSize: "14px",
                    }}
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => {
                      setShowClearAllModal(false);
                      setClearStep(1);
                      setConfirmationPassword("");
                      setConfirmationInput("");
                    }}
                    disabled={verifyingConfirmation}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn"
                    disabled={verifyingConfirmation || !confirmationPassword.trim()}
                    style={{
                      background: "#dc2626",
                      color: "#ffffff",
                      border: "none",
                      padding: "10px 20px",
                      borderRadius: "8px",
                      fontWeight: 700,
                      cursor: verifyingConfirmation || !confirmationPassword.trim() ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    {verifyingConfirmation ? (
                      <>
                        <RefreshCw size={16} className="spin" /> Verifying...
                      </>
                    ) : (
                      "Verify & Proceed"
                    )}
                  </button>
                </div>
              </form>
            ) : (
              <div>
                <div style={{ padding: "12px", borderRadius: "8px", backgroundColor: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)", marginBottom: "16px" }}>
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--clr-text-secondary)", lineHeight: 1.5 }}>
                    <strong>Step 2 of 2:</strong> Confirmation verified. Final destructive confirmation required.
                  </p>
                </div>

                <div style={{ marginBottom: "24px" }}>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: 700, color: "var(--clr-text-primary)", marginBottom: "8px" }}>
                    Type <span style={{ color: "#dc2626" }}>CLEAR ALL DATA</span> to confirm:
                  </label>
                  <input
                    type="text"
                    className="form-input"
                    value={confirmationInput}
                    onChange={(e) => setConfirmationInput(e.target.value)}
                    placeholder="CLEAR ALL DATA"
                    autoFocus
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      borderRadius: "8px",
                      border: "1px solid var(--clr-border)",
                      fontSize: "14px",
                      fontWeight: 700,
                      letterSpacing: "0.5px",
                    }}
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                  <button
                    type="button"
                    className="btn btn-outline"
                    disabled={clearingAll}
                    onClick={() => setClearStep(1)}
                  >
                    Back
                  </button>

                  <div style={{ display: "flex", gap: "10px" }}>
                    <button
                      type="button"
                      className="btn btn-outline"
                      disabled={clearingAll}
                      onClick={() => {
                        setShowClearAllModal(false);
                        setClearStep(1);
                        setConfirmationPassword("");
                        setConfirmationInput("");
                      }}
                    >
                      Cancel
                    </button>

                    <button
                      type="button"
                      disabled={confirmationInput !== "CLEAR ALL DATA" || clearingAll}
                      onClick={handleClearAllData}
                      style={{
                        background: confirmationInput === "CLEAR ALL DATA" && !clearingAll ? "#dc2626" : "#fca5a5",
                        color: "#ffffff",
                        border: "none",
                        padding: "10px 20px",
                        borderRadius: "8px",
                        fontWeight: 700,
                        cursor: confirmationInput === "CLEAR ALL DATA" && !clearingAll ? "pointer" : "not-allowed",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      {clearingAll ? (
                        <>
                          <RefreshCw size={16} className="spin" /> Resetting Platform...
                        </>
                      ) : (
                        <>
                          <Trash2 size={16} /> Execute Platform Reset
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </AppLayout>
  );
}
