/**
 * GreenNexa — Centralized Optimal Score Calculation.
 *
 * Starts from 100%.
 * For each ACTIVE anomaly, subtracts the corresponding severity penalty:
 *   Critical = -20%
 *   High = -10%
 *   Medium = -5%
 *   Low = -2%
 *
 * Score is COMMON across all anomaly modules (Energy, Water, Waste, etc.).
 * Resolved and Dismissed anomalies do not contribute penalty.
 * Score is NOT forced to zero (can go negative).
 * Never returns NaN or Infinity.
 */

export const SEVERITY_PENALTIES: Record<string, number> = {
  CRITICAL: 20,
  HIGH: 10,
  MEDIUM: 5,
  LOW: 2,
};

export function calculateOptimalScore(
  anomalies: Array<{ severity?: string; status?: string }>
): number {
  if (!Array.isArray(anomalies) || anomalies.length === 0) {
    return 100;
  }

  const active = anomalies.filter((a) => {
    if (!a.status) return true;
    const st = a.status.toUpperCase();
    return st === "OPEN" || st === "ACKNOWLEDGED";
  });

  let score = 100;
  for (const a of active) {
    const sev = (a.severity || "").toUpperCase().trim();
    const penalty = SEVERITY_PENALTIES[sev] ?? 0;
    score -= penalty;
  }

  if (isNaN(score) || !isFinite(score)) {
    return 100;
  }
  return score;
}

export function getOptimalScoreColorAndLabel(score: number): {
  color: string;
  label: string;
} {
  if (score < 60) {
    return { color: "#ef4444", label: "CRITICAL ACTION REQUIRED" };
  }
  if (score < 85) {
    return { color: "#f59e0b", label: "ATTENTION REQUIRED" };
  }
  return { color: "#10b981", label: "OPTIMAL HEALTH" };
}
