import React from "react";
import { Inbox, AlertCircle } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export function EmptyState({
  title = "No data available",
  description = "There are no records matching your request at this time.",
  icon,
  action,
}: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        background: "var(--clr-surface)",
        borderRadius: "16px",
        border: "1px dashed var(--clr-border)",
      }}
    >
      <div
        style={{
          width: "56px",
          height: "56px",
          borderRadius: "50%",
          background: "var(--clr-surface-2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "16px",
          color: "var(--clr-text-muted)",
        }}
      >
        {icon || <Inbox size={28} />}
      </div>
      <h3 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px", color: "var(--clr-text-primary)" }}>{title}</h3>
      <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", maxWidth: "420px", marginBottom: action ? "20px" : "0" }}>
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  );
}
