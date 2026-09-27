"use client";

import React from "react";

interface RedDotIndicatorProps {
  label?: string;
  size?: "sm" | "md" | "lg";
  style?: React.CSSProperties;
  className?: string;
}

export function RedDotIndicator({
  label = "Unread anomaly",
  size = "md",
  style = {},
  className = "",
}: RedDotIndicatorProps) {
  const px = size === "sm" ? 8 : size === "lg" ? 12 : 10;

  return (
    <span
      className={className}
      style={{
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: `${px}px`,
        height: `${px}px`,
        flexShrink: 0,
        ...style,
      }}
      title={label}
      aria-label={label}
      role="status"
    >
      {/* Static red dot */}
      <span
        style={{
          position: "relative",
          width: `${px}px`,
          height: `${px}px`,
          borderRadius: "50%",
          backgroundColor: "#ef4444",
          boxShadow: "0 0 3px rgba(239, 68, 68, 0.6)",
          display: "inline-block",
        }}
      />
      <span
        style={{
          position: "absolute",
          width: "1px",
          height: "1px",
          padding: 0,
          margin: "-1px",
          overflow: "hidden",
          clip: "rect(0, 0, 0, 0)",
          border: 0,
        }}
      >
        {label}
      </span>
    </span>
  );
}

export default RedDotIndicator;
