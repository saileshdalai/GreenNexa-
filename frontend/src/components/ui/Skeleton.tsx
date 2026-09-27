import React from "react";

interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ width = "100%", height = "20px", borderRadius = "8px", className = "", style = {} }: SkeletonProps) {
  return (
    <div
      className={`skeleton-loader ${className}`}
      style={{
        width,
        height,
        borderRadius,
        backgroundColor: "var(--clr-surface-2)",
        opacity: 0.7,
        animation: "pulse 1.5s infinite ease-in-out",
        ...style,
      }}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="card" style={{ padding: "20px" }}>
      <Skeleton width="40%" height="16px" style={{ marginBottom: "12px" }} />
      <Skeleton width="60%" height="32px" style={{ marginBottom: "16px" }} />
      <Skeleton width="80%" height="14px" />
    </div>
  );
}
