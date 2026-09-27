"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { X, MapPin, Loader2, Plus } from "lucide-react";

interface AddWardModalProps {
  municipalityId: string;
  municipalityName: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function AddWardModal({
  municipalityId,
  municipalityName,
  isOpen,
  onClose,
  onSuccess,
}: AddWardModalProps) {
  const { showToast } = useToast();
  const [wardName, setWardName] = useState("");
  const [wardNumber, setWardNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = wardName.trim();
    if (!cleanName) {
      setErrorMsg("Ward name is required.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    try {
      // POST to /wards — creates a MunicipalityWard record, NOT a FacilityBlock
      const payload: { ward_name: string; ward_number?: string } = {
        ward_name: cleanName,
      };
      if (wardNumber.trim()) {
        payload.ward_number = wardNumber.trim();
      }

      await api.post(`/api/v1/organisations/${municipalityId}/wards`, payload);
      showToast(`Ward "${cleanName}" added successfully!`, "success");
      setWardName("");
      setWardNumber("");
      window.dispatchEvent(new CustomEvent("greennexa_telemetry_updated"));
      window.dispatchEvent(new CustomEvent("greennexa_wards_updated"));
      onSuccess?.();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to add ward.");
      showToast(err.message || "Failed to add ward.", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: "460px",
          padding: "24px",
          backgroundColor: "var(--clr-surface)",
          border: "1px solid var(--clr-border)",
          borderRadius: "12px",
          boxShadow: "0 20px 40px -10px rgba(0,0,0,0.5)",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(2, 132, 199, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <MapPin size={18} color="#0284c7" />
            </div>
            <div>
              <h2
                style={{
                  fontSize: "16px",
                  fontWeight: 800,
                  margin: 0,
                  color: "var(--clr-text-primary)",
                }}
              >
                Add Ward
              </h2>
              <p
                style={{
                  fontSize: "12px",
                  margin: 0,
                  color: "var(--clr-text-muted)",
                }}
              >
                {municipalityName}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--clr-text-muted)",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {errorMsg && (
          <div
            style={{
              padding: "10px 12px",
              borderRadius: "8px",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#fca5a5",
              fontSize: "13px",
              marginBottom: "16px",
            }}
          >
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                display: "block",
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--clr-text-primary)",
                marginBottom: "6px",
              }}
            >
              Ward Name <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Ward 1 - Main Bazaar"
              value={wardName}
              onChange={(e) => setWardName(e.target.value)}
              required
              autoFocus
              style={{ width: "100%", padding: "10px 12px" }}
            />
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label
              style={{
                display: "block",
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--clr-text-primary)",
                marginBottom: "6px",
              }}
            >
              Ward Number{" "}
              <span style={{ fontSize: "11px", color: "var(--clr-text-muted)" }}>
                (optional)
              </span>
            </label>
            <input
              type="text"
              className="input"
              placeholder="e.g. 11"
              value={wardNumber}
              onChange={(e) => setWardNumber(e.target.value)}
              style={{ width: "100%", padding: "10px 12px" }}
            />
          </div>

          <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={onClose}
              disabled={loading}
              style={{ padding: "8px 16px" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !wardName.trim()}
              style={{
                padding: "8px 18px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Adding...
                </>
              ) : (
                <>
                  <Plus size={14} /> Add Ward
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
