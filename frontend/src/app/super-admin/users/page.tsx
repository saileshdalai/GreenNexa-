"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { SuperAdminUserItem, Organisation, OrganisationListResponse } from "@/types";
import {
  Users,
  UserPlus,
  Shield,
  KeyRound,
  Power,
  Search,
  RefreshCw,
  Mail,
  Building,
} from "lucide-react";

export default function UsersManagementPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  const [users, setUsers] = useState<SuperAdminUserItem[]>([]);
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showResetModal, setShowResetModal] = useState<boolean>(false);
  const [selectedUser, setSelectedUser] = useState<SuperAdminUserItem | null>(null);

  // New Admin Form
  const [fullName, setFullName] = useState<string>("");
  const [userIdInput, setUserIdInput] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [phone, setPhone] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [role, setRole] = useState<string>("ADMIN");

  // Reset password state
  const [resetStep, setResetStep] = useState<1 | 2>(1);
  const [confirmationPassword, setConfirmationPassword] = useState<string>("");
  const [newPassword, setNewPassword] = useState<string>("");
  const [confirmNewPassword, setConfirmNewPassword] = useState<string>("");
  const [verifyingConfirmation, setVerifyingConfirmation] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [uData, oData] = await Promise.all([
        api.get<SuperAdminUserItem[]>("/api/v1/super-admin/users"),
        api.get<OrganisationListResponse | Organisation[]>("/api/v1/organisations"),
      ]);
      setUsers(uData);
      const orgList = Array.isArray(oData) ? oData : oData?.items || [];
      setOrganisations(orgList);
      if (orgList.length > 0 && !selectedOrgId) {
        setSelectedOrgId(orgList[0].id);
      }
    } catch (err: any) {
      showToast(err.message || "Failed to load users data", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.role !== "SUPER_ADMIN") {
      router.push("/dashboard");
      return;
    }
    loadData();
  }, [user]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName || !email || !password || !selectedOrgId) {
      return showToast("Please fill all required fields", "error");
    }

    setSubmitting(true);
    try {
      await api.post("/api/v1/super-admin/users", {
        full_name: fullName.trim(),
        user_id: userIdInput.trim() || undefined,
        email: email.trim().toLowerCase(),
        phone: phone.trim() || undefined,
        password: password,
        organisation_id: selectedOrgId,
        role: role,
      });

      showToast("User account created successfully!", "success");
      setShowCreateModal(false);
      setFullName("");
      setEmail("");
      setPassword("");
      loadData();
    } catch (err: any) {
      showToast(err.message || "Failed to create user account", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyResetConfirmation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!confirmationPassword.trim()) {
      return showToast("Please enter the confirmation password", "error");
    }

    setVerifyingConfirmation(true);
    try {
      await api.post("/api/v1/super-admin/verify-confirmation-password", {
        confirmation_password: confirmationPassword,
      });
      setResetStep(2);
    } catch (err: any) {
      showToast(err.message || "Invalid confirmation password", "error");
    } finally {
      setVerifyingConfirmation(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    if (!newPassword || newPassword.length < 6) {
      return showToast("New password must be at least 6 characters", "error");
    }
    if (newPassword !== confirmNewPassword) {
      return showToast("Passwords do not match", "error");
    }

    setSubmitting(true);
    try {
      await api.post(`/api/v1/super-admin/users/${selectedUser.id}/reset-password`, {
        confirmation_password: confirmationPassword,
        new_password: newPassword,
        confirm_new_password: confirmNewPassword,
      });
      showToast(`Password reset successfully for ${selectedUser.email}`, "success");
      setShowResetModal(false);
      setResetStep(1);
      setConfirmationPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
      setSelectedUser(null);
    } catch (err: any) {
      showToast(err.message || "Failed to reset password", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleUserActive = async (u: SuperAdminUserItem) => {
    try {
      await api.put(`/api/v1/super-admin/users/${u.id}`, {
        is_active: !u.is_active,
      });
      showToast(`Account status updated for ${u.email}`, "success");
      loadData();
    } catch (err: any) {
      showToast(err.message || "Failed to update account status", "error");
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.organisation_name && u.organisation_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <AppLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)", display: "flex", alignItems: "center", gap: "10px" }}>
            <Users color="var(--clr-primary)" size={28} />
            Users / Admins Management
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginTop: "4px" }}>
            Manage platform administrator accounts, credentials, access levels, and security states.
          </p>
        </div>

        <div style={{ display: "flex", gap: "12px" }}>
          <button onClick={loadData} className="btn btn-outline btn-sm" title="Refresh">
            <RefreshCw size={14} className={loading ? "spin" : ""} />
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn btn-primary btn-md" style={{ gap: "8px", fontWeight: 700 }}>
            <UserPlus size={18} />
            <span>+ Create Admin Account</span>
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="card" style={{ padding: "20px", marginBottom: "24px" }}>
        <div style={{ position: "relative" }}>
          <Search size={16} color="var(--clr-text-muted)" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            className="form-input"
            placeholder="Search by Admin name, User ID, Email, or Organisation..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ paddingLeft: "36px" }}
          />
        </div>
      </div>

      {/* Users Table */}
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ background: "var(--clr-surface-2)", borderBottom: "2px solid var(--clr-border)", textAlign: "left", color: "var(--clr-text-muted)", fontSize: "12px", fontWeight: 700, textTransform: "uppercase" }}>
                <th style={{ padding: "14px 20px" }}>Admin Name & User ID</th>
                <th style={{ padding: "14px 20px" }}>Organisation</th>
                <th style={{ padding: "14px 20px" }}>Email / Phone</th>
                <th style={{ padding: "14px 20px" }}>Role</th>
                <th style={{ padding: "14px 20px" }}>Status</th>
                <th style={{ padding: "14px 20px" }}>Created Date</th>
                <th style={{ padding: "14px 20px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "40px", textAlign: "center", color: "var(--clr-text-muted)" }}>
                    {loading ? "Loading users..." : "No user accounts found."}
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <tr key={u.id} style={{ borderBottom: "1px solid var(--clr-border-light)" }} className="table-row-hover">
                    <td style={{ padding: "16px 20px" }}>
                      <div style={{ fontWeight: 800, fontSize: "14px", color: "var(--clr-text-primary)" }}>{u.full_name}</div>
                      <div style={{ fontSize: "11px", color: "var(--clr-primary)", fontFamily: "monospace", fontWeight: 700 }}>{u.id}</div>
                    </td>

                    <td style={{ padding: "16px 20px" }}>
                      <div style={{ fontWeight: 600, color: "var(--clr-text-primary)" }}>{u.organisation_name || "Platform Wide"}</div>
                      <div style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>{u.organisation_id || "SYSTEM"}</div>
                    </td>

                    <td style={{ padding: "16px 20px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <Mail size={13} color="var(--clr-text-muted)" />
                        {u.email}
                      </div>
                      {u.phone && <div style={{ fontSize: "11px", color: "var(--clr-text-muted)", marginTop: "2px" }}>{u.phone}</div>}
                    </td>

                    <td style={{ padding: "16px 20px" }}>
                      <span style={{ fontSize: "11px", fontWeight: 800, padding: "3px 8px", borderRadius: "6px", background: u.role === "SUPER_ADMIN" ? "rgba(139, 92, 246, 0.15)" : "var(--clr-primary-light)", color: u.role === "SUPER_ADMIN" ? "#8b5cf6" : "var(--clr-primary)" }}>
                        {u.role}
                      </span>
                    </td>

                    <td style={{ padding: "16px 20px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 700, padding: "3px 8px", borderRadius: "9999px", background: u.is_active ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)", color: u.is_active ? "#10b981" : "#ef4444" }}>
                        {u.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>

                    <td style={{ padding: "16px 20px", color: "var(--clr-text-muted)" }}>
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>

                    <td style={{ padding: "16px 20px", textAlign: "right" }}>
                      <div style={{ display: "flex", gap: "6px", justifyContent: "flex-end" }}>
                        <button
                          onClick={() => {
                            setSelectedUser(u);
                            setResetStep(1);
                            setConfirmationPassword("");
                            setNewPassword("");
                            setConfirmNewPassword("");
                            setShowResetModal(true);
                          }}
                          className="btn btn-outline btn-sm"
                          style={{ gap: "4px", fontSize: "12px" }}
                          title="Reset Password"
                        >
                          <KeyRound size={13} /> Reset Password
                        </button>

                        <button
                          onClick={() => handleToggleUserActive(u)}
                          className="btn btn-outline btn-sm"
                          style={{ color: u.is_active ? "#ef4444" : "#10b981" }}
                          title={u.is_active ? "Disable User" : "Enable User"}
                        >
                          <Power size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* CREATE ADMIN MODAL */}
      {showCreateModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.6)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
          <div className="card" style={{ width: "100%", maxWidth: "520px", padding: "28px" }}>
            <h2 style={{ fontSize: "20px", fontWeight: 800, marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <UserPlus color="var(--clr-primary)" /> Create Admin Account
            </h2>

            <form onSubmit={handleCreateUser} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div className="form-group">
                <label className="form-label">Admin Name *</label>
                <input type="text" className="form-input" placeholder="Full Name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              </div>

              <div className="form-group">
                <label className="form-label">User ID (Optional)</label>
                <input type="text" className="form-input" placeholder="e.g. ABC_ADMIN" value={userIdInput} onChange={(e) => setUserIdInput(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Email Address *</label>
                <input type="email" className="form-input" placeholder="admin@org.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>

              <div className="form-group">
                <label className="form-label">Phone Number (Optional)</label>
                <input type="text" className="form-input" placeholder="+91 98765 43210" value={phone} onChange={(e) => setPhone(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Assign Organisation *</label>
                <select className="form-input" value={selectedOrgId} onChange={(e) => setSelectedOrgId(e.target.value)}>
                  {organisations.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name} ({o.id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Role</label>
                <select className="form-input" value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="ADMIN">ADMIN</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Initial Password *</label>
                <input type="password" className="form-input" placeholder="Minimum 6 characters" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </div>

              <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end", marginTop: "12px" }}>
                <button type="button" onClick={() => setShowCreateModal(false)} className="btn btn-outline">
                  Cancel
                </button>
                <button type="submit" disabled={submitting} className="btn btn-primary">
                  {submitting ? "Creating..." : "Create Admin Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RESET PASSWORD MODAL - 2-STEP CONFIRMATION FLOW */}
      {showResetModal && selectedUser && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.6)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
          <div className="card" style={{ width: "100%", maxWidth: "460px", padding: "28px" }}>
            <h2 style={{ fontSize: "20px", fontWeight: 800, marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
              <KeyRound color="var(--clr-primary)" /> Reset Password
            </h2>
            <p style={{ fontSize: "13px", color: "var(--clr-text-secondary)", marginBottom: "16px" }}>
              Target Account: <strong>{selectedUser.full_name}</strong> ({selectedUser.email})
            </p>

            {resetStep === 1 ? (
              <form onSubmit={handleVerifyResetConfirmation} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ padding: "12px", borderRadius: "8px", backgroundColor: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.2)" }}>
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--clr-text-secondary)", lineHeight: 1.5 }}>
                    <strong>Step 1 of 2:</strong> Enter the confirmation password to authorize resetting this account&apos;s password.
                  </p>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 700 }}>Confirmation Password *</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="Enter confirmation password"
                    value={confirmationPassword}
                    onChange={(e) => setConfirmationPassword(e.target.value)}
                    required
                    autoFocus
                  />
                </div>

                <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end", marginTop: "12px" }}>
                  <button
                    type="button"
                    onClick={() => {
                      setShowResetModal(false);
                      setResetStep(1);
                      setConfirmationPassword("");
                    }}
                    className="btn btn-outline"
                    disabled={verifyingConfirmation}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={verifyingConfirmation || !confirmationPassword.trim()}
                    className="btn btn-primary"
                  >
                    {verifyingConfirmation ? "Verifying..." : "Verify & Continue"}
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleResetPassword} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ padding: "12px", borderRadius: "8px", backgroundColor: "rgba(16, 185, 129, 0.08)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--clr-text-secondary)", lineHeight: 1.5 }}>
                    <strong>Step 2 of 2:</strong> Authorization verified. Enter the new secure password.
                  </p>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 700 }}>New Password *</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="Enter new password (min. 6 characters)"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={6}
                    autoFocus
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 700 }}>Confirm New Password *</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="Re-enter new password to confirm"
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    required
                    minLength={6}
                  />
                </div>

                <div style={{ display: "flex", gap: "12px", justifyContent: "space-between", marginTop: "12px" }}>
                  <button
                    type="button"
                    onClick={() => setResetStep(1)}
                    className="btn btn-outline"
                    disabled={submitting}
                  >
                    Back
                  </button>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button
                      type="button"
                      onClick={() => {
                        setShowResetModal(false);
                        setResetStep(1);
                        setConfirmationPassword("");
                        setNewPassword("");
                        setConfirmNewPassword("");
                      }}
                      className="btn btn-outline"
                      disabled={submitting}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting || !newPassword || !confirmNewPassword}
                      className="btn btn-primary"
                    >
                      {submitting ? "Updating..." : "Reset Password"}
                    </button>
                  </div>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </AppLayout>
  );
}
