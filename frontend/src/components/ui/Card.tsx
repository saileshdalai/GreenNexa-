import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}

export function Card({ children, className = "", style = {}, onClick }: CardProps) {
  return (
    <div
      className={`card ${className}`}
      onClick={onClick}
      style={{
        cursor: onClick ? "pointer" : "default",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  trend?: string;
  trendType?: "positive" | "negative" | "neutral";
  icon?: React.ReactNode;
  subtitle?: string;
  color?: string;
}

export function MetricCard({ title, value, unit, trend, trendType = "neutral", icon, subtitle, color }: MetricCardProps) {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "var(--clr-text-secondary)" }}>{title}</span>
          {icon && (
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                backgroundColor: color || "var(--clr-primary-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--clr-primary)",
              }}
            >
              {icon}
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "baseline", gap: "6px", marginBottom: "4px" }}>
          <span style={{ fontSize: "28px", fontWeight: 800, color: "var(--clr-text-primary)" }}>{value}</span>
          {unit && <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--clr-text-muted)" }}>{unit}</span>}
        </div>
      </div>

      {(trend || subtitle) && (
        <div style={{ marginTop: "12px", paddingTop: "8px", borderTop: "1px solid var(--clr-border-light)", display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "12px" }}>
          {trend && (
            <span
              style={{
                fontWeight: 600,
                color:
                  trendType === "positive"
                    ? "var(--clr-success)"
                    : trendType === "negative"
                    ? "var(--clr-error)"
                    : "var(--clr-text-muted)",
              }}
            >
              {trend}
            </span>
          )}
          {subtitle && <span style={{ color: "var(--clr-text-muted)" }}>{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
