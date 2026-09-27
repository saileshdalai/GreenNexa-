"use client";

import React from "react";
import { useToast } from "@/context/ToastContext";
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from "lucide-react";

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div style={{
      position: "fixed",
      bottom: "24px",
      right: "24px",
      zIndex: 9999,
      display: "flex",
      flexDirection: "column",
      gap: "8px",
      maxWidth: "360px",
      width: "100%",
      pointerEvents: "none",
    }}>
      {toasts.map((t) => (
        <div
          key={t.id}
          style={{
            pointerEvents: "auto",
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
            padding: "14px 16px",
            borderRadius: "12px",
            background: "var(--clr-surface)",
            border: `1px solid ${
              t.type === "success"
                ? "var(--clr-success)"
                : t.type === "error"
                ? "var(--clr-error)"
                : t.type === "warning"
                ? "var(--clr-warning)"
                : "var(--clr-info)"
            }`,
            boxShadow: "var(--shadow-lg)",
            color: "var(--clr-text-primary)",
            fontSize: "14px",
            animation: "slideIn 0.2s ease-out",
          }}
        >
          {t.type === "success" && <CheckCircle2 size={18} color="var(--clr-success)" style={{ marginTop: "2px", flexShrink: 0 }} />}
          {t.type === "warning" && <AlertTriangle size={18} color="var(--clr-warning)" style={{ marginTop: "2px", flexShrink: 0 }} />}
          {t.type === "error" && <AlertCircle size={18} color="var(--clr-error)" style={{ marginTop: "2px", flexShrink: 0 }} />}
          {t.type === "info" && <Info size={18} color="var(--clr-info)" style={{ marginTop: "2px", flexShrink: 0 }} />}

          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600 }}>{t.title}</div>
            {t.message && <div style={{ fontSize: "12px", color: "var(--clr-text-secondary)", marginTop: "2px" }}>{t.message}</div>}
          </div>

          <button
            onClick={() => removeToast(t.id)}
            style={{ color: "var(--clr-text-muted)", cursor: "pointer", border: "none", background: "none" }}
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
