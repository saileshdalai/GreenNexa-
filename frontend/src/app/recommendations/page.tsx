"use client";

import React, { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { AIRecommendation, RecommendationListResponse, RecommendationStatus } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Lightbulb, RefreshCw, CheckCircle, XCircle, ArrowRight } from "lucide-react";

export default function RecommendationsPage() {
  const { activeOrgId, user } = useAuth();
  const { showToast } = useToast();
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("OPEN");
  const [loading, setLoading] = useState<boolean>(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const loadRecommendations = async () => {
    if (!activeOrgId) return;
    setLoading(true);
    try {
      const params: Record<string, any> = { organisation_id: activeOrgId };
      if (statusFilter !== "ALL") params.status = statusFilter;

      const res = await api.get<RecommendationListResponse | AIRecommendation[]>(`/api/v1/recommendations`, params);
      const items = Array.isArray(res) ? res : Array.isArray((res as RecommendationListResponse)?.items) ? (res as RecommendationListResponse).items : [];
      setRecommendations(items);
    } catch {
      setRecommendations([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendations();

    const handleFocus = () => {
      loadRecommendations();
    };
    const handleDemoChange = () => {
      loadRecommendations();
    };

    window.addEventListener("focus", handleFocus);
    window.addEventListener("greennexa_demo_mode_changed", handleDemoChange);

    return () => {
      window.removeEventListener("focus", handleFocus);
      window.removeEventListener("greennexa_demo_mode_changed", handleDemoChange);
    };
  }, [activeOrgId, statusFilter]);

  const updateStatus = async (id: string, newStatus: RecommendationStatus) => {
    setUpdatingId(id);
    try {
      await api.patch(`/api/v1/recommendations/${id}/status`, { status: newStatus });
      showToast(`Recommendation marked as ${newStatus}`, "success");
      loadRecommendations();
    } catch (err: any) {
      showToast(err.message || "Failed to update recommendation status", "error");
    } finally {
      setUpdatingId(null);
    }
  };

  const safeRecommendations = (Array.isArray(recommendations) ? recommendations : []).filter((rec) => {
    if (statusFilter === "OPEN") {
      return rec.status === "OPEN" || rec.status === "ACTIVE";
    }
    if (statusFilter === "RESOLVED") {
      return rec.status === "RESOLVED" || rec.status === "ACTIONED";
    }
    if (statusFilter === "DISMISSED") {
      return rec.status === "DISMISSED";
    }
    if (statusFilter === "ACKNOWLEDGED") {
      return rec.status === "ACKNOWLEDGED";
    }
    return true;
  });

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px" }}>
            <Lightbulb color="var(--clr-primary)" /> AI Recommendations Board
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)" }}>
            Actionable sustainability decision-support based on statistical patterns & anomalies
          </p>
        </div>

        <button onClick={loadRecommendations} className="btn btn-outline btn-sm">
          <RefreshCw size={14} className={loading ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="card" style={{ padding: "12px 20px", marginBottom: "24px", display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "14px", fontWeight: 600 }}>Status:</span>
        {["OPEN", "ACKNOWLEDGED", "RESOLVED", "DISMISSED", "ALL"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`btn btn-sm ${statusFilter === st ? "btn-primary" : "btn-outline"}`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Recommendations List */}
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <Skeleton height="120px" />
          <Skeleton height="120px" />
        </div>
      ) : safeRecommendations.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {safeRecommendations.map((rec) => {
            const recTitle = rec.title || rec.summary || "AI Optimization Plan";
            const targetMetric = rec.target_metric || rec.metric || "energy";
            const explanationText = rec.explanation || rec.confidence_note || rec.summary || "";
            const actionText = rec.suggested_action || (Array.isArray(rec.recommended_actions) && rec.recommended_actions.length > 0 ? rec.recommended_actions.join("; ") : "Investigate facility telemetry");
            return (
              <div
                key={rec.id}
                className="card"
                style={{
                  padding: "20px",
                  borderLeft: `4px solid ${
                    rec.priority === "CRITICAL" || rec.priority === "HIGH" ? "var(--clr-error)" : "var(--clr-primary)"
                  }`,
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px", marginBottom: "12px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                      <h3 style={{ fontSize: "18px", fontWeight: 700 }}>{recTitle}</h3>
                      <Badge variant={rec.priority === "CRITICAL" || rec.priority === "HIGH" ? "error" : "primary"}>
                        {rec.priority}
                      </Badge>
                      <Badge variant={rec.status === "RESOLVED" ? "success" : rec.status === "ACKNOWLEDGED" ? "info" : "neutral"}>
                        {rec.status}
                      </Badge>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--clr-text-muted)" }}>
                      Target Metric: <strong style={{ textTransform: "capitalize" }}>{targetMetric}</strong>
                      {rec.facility_id ? (
                        <> | Block / Location: <strong style={{ color: "var(--clr-text-primary)" }}>{rec.facility_id}</strong></>
                      ) : null}
                      {" "}| Created: {new Date(rec.created_at).toLocaleString()}
                    </div>
                  </div>

                  {/* Status Action Buttons */}
                  {rec.status !== "RESOLVED" && rec.status !== "DISMISSED" && (
                    <div style={{ display: "flex", gap: "8px" }}>
                      {(rec.status === "OPEN" || rec.status === "ACTIVE") && (
                        <button
                          onClick={() => updateStatus(rec.id, "ACKNOWLEDGED")}
                          disabled={updatingId === rec.id}
                          className="btn btn-outline btn-sm"
                        >
                          Acknowledge
                        </button>
                      )}
                      <button
                        onClick={() => updateStatus(rec.id, "RESOLVED")}
                        disabled={updatingId === rec.id}
                        className="btn btn-primary btn-sm"
                        style={{ display: "flex", alignItems: "center", gap: "4px" }}
                      >
                        <CheckCircle size={14} /> Resolve
                      </button>
                      <button
                        onClick={() => updateStatus(rec.id, "DISMISSED")}
                        disabled={updatingId === rec.id}
                        className="btn btn-outline btn-sm"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>

                {explanationText && (
                  <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)", marginBottom: "12px", lineHeight: "1.6" }}>
                    {explanationText}
                  </p>
                )}

                <div
                  style={{
                    padding: "12px 16px",
                    borderRadius: "8px",
                    background: "var(--clr-surface-2)",
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "var(--clr-primary-dark)",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <ArrowRight size={16} /> Suggested Action: {actionText}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState title="No recommendations found" description={`There are no recommendations in '${statusFilter}' status.`} />
      )}
    </AppLayout>
  );
}
