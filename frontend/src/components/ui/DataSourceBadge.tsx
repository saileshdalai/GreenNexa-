import React from "react";
import { DataSourceType } from "@/types";
import { Cpu, Activity } from "lucide-react";

interface DataSourceBadgeProps {
  source?: DataSourceType;
  size?: "sm" | "md";
}

export function DataSourceBadge({ source = "synthetic", size = "md" }: DataSourceBadgeProps) {
  const isSynthetic = source === "synthetic";

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        padding: size === "sm" ? "2px 10px" : "6px 14px",
        borderRadius: "9999px",
        fontSize: size === "sm" ? "12px" : "13px",
        fontWeight: 600,
        backgroundColor: isSynthetic ? "rgba(59, 130, 246, 0.1)" : "rgba(34, 197, 94, 0.1)",
        color: isSynthetic ? "#2563eb" : "#16a34a",
        border: `1px solid ${isSynthetic ? "rgba(59, 130, 246, 0.2)" : "rgba(34, 197, 94, 0.2)"}`,
      }}
    >
      <span
        style={{
          width: size === "sm" ? "6px" : "8px",
          height: size === "sm" ? "6px" : "8px",
          borderRadius: "50%",
          backgroundColor: isSynthetic ? "#2563eb" : "#16a34a",
          boxShadow: isSynthetic ? "0 0 6px rgba(37,99,235,0.6)" : "0 0 6px rgba(22,163,74,0.6)",
        }}
      />
      {isSynthetic ? (
        <>
          <Activity size={size === "sm" ? 12 : 14} />
          <span>Synthetic Simulator</span>
        </>
      ) : (
        <>
          <Cpu size={size === "sm" ? 12 : 14} />
          <span>Real IoT Sensors</span>
        </>
      )}
    </div>
  );
}
