import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "success" | "warning" | "error" | "info" | "neutral" | "primary";
  size?: "sm" | "md";
}

export function Badge({ children, variant = "neutral", size = "md" }: BadgeProps) {
  const getStyle = () => {
    switch (variant) {
      case "success":
        return { bg: "#dcfce7", color: "#15803d", border: "#bbf7d0" };
      case "warning":
        return { bg: "#fef3c7", color: "#b45309", border: "#fde68a" };
      case "error":
        return { bg: "#fee2e2", color: "#b91c1c", border: "#fca5a5" };
      case "info":
        return { bg: "#dbeafe", color: "#1d4ed8", border: "#bfdbfe" };
      case "primary":
        return { bg: "var(--clr-primary-light)", color: "var(--clr-primary-dark)", border: "var(--clr-border)" };
      default:
        return { bg: "#f3f4f6", color: "#4b5563", border: "#e5e7eb" };
    }
  };

  const colors = getStyle();

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: size === "sm" ? "2px 8px" : "4px 12px",
        borderRadius: "9999px",
        fontSize: size === "sm" ? "11px" : "12px",
        fontWeight: 600,
        backgroundColor: colors.bg,
        color: colors.color,
        border: `1px solid ${colors.border}`,
        whiteSpace: "nowrap",
        letterSpacing: "0.02em",
      }}
    >
      {children}
    </span>
  );
}
