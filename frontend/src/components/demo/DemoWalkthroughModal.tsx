"use client";

import React from "react";
import { useDemo } from "@/context/DemoContext";

const STEPS = [
  {
    step: 1,
    title: "Step 1: Facility Overview & Health Monitoring",
    badge: "Dashboard Overview",
    description:
      "GreenNexa aggregates multi-metric sustainability data across Energy, Water, Waste, Temperature, Humidity, and CO2. The Facility Health Indicator monitors overall operational safety in real time.",
    actionHint: "Look at the top KPI summary cards and Facility Health Indicator on the main dashboard.",
  },
  {
    step: 2,
    title: "Step 2: Live Sensor Data Ingestion",
    badge: "IoT & Synthetic Simulation",
    description:
      "Sensor data streams into GreenNexa either via physical ESP32/Wokwi microcontrollers (via /api/v1/iot/sensor-data) or through the synthetic simulator engine running 3-minute background generation cycles.",
    actionHint: "Click 'Generate Reading' on the Demo Control Panel to instantly simulate a live telemetry ping.",
  },
  {
    step: 3,
    title: "Step 3: Real-Time AI Anomaly Detection",
    badge: "Anomaly Engine",
    description:
      "When a sensor reading strays outside expected baseline thresholds (e.g. Energy spiking to 1850 kWh), GreenNexa's automated anomaly detector identifies the deviation and classifies severity (LOW, MEDIUM, HIGH, CRITICAL).",
    actionHint: "Click 'Generate Demo Anomaly' on the Demo Control Panel to simulate a HIGH severity spike.",
  },
  {
    step: 4,
    title: "Step 4: Intelligent AI Recommendations",
    badge: "Decision Support",
    description:
      "Anomalies trigger the GreenNexa AI Recommender, which analyzes root causes and provides actionable steps (e.g. 'Inspect HVAC compressor schedules and check high-load equipment').",
    actionHint: "Review the AI Insights section on the dashboard or navigate to /recommendations.",
  },
  {
    step: 5,
    title: "Step 5: Predictive Holt-Winters Forecasting",
    badge: "ML Forecasting",
    description:
      "GreenNexa analyzes historical consumption patterns using Holt-Winters additive exponential smoothing to project upcoming energy and water usage trends for proactive facility management.",
    actionHint: "Navigate to /forecast to inspect 7-day predicted consumption graphs.",
  },
  {
    step: 6,
    title: "Step 6: Automated Alerts & In-App Messaging",
    badge: "Alerts & Messages",
    description:
      "HIGH and CRITICAL anomalies immediately generate in-app notification alerts for facility administrators and trigger role-scoped escalation threads.",
    actionHint: "Check the top navigation Notification Bell or visit /messages to view admin communications.",
  },
  {
    step: 7,
    title: "Step 7: Downloadable Compliance Reports",
    badge: "Reports & PDF/CSV",
    description:
      "Generate audit-ready facility sustainability reports in CSV or formatted PDF document formats for compliance filing and stakeholder review.",
    actionHint: "Navigate to /reports to test instant CSV and PDF downloads.",
  },
];

export const DemoWalkthroughModal: React.FC = () => {
  const { walkthroughOpen, currentWalkthroughStep, stopWalkthrough, nextWalkthroughStep, prevWalkthroughStep, setWalkthroughStep } = useDemo();

  if (!walkthroughOpen) return null;

  const current = STEPS.find((s) => s.step === currentWalkthroughStep) || STEPS[0];

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(4px)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <div
        style={{
          backgroundColor: "#1e293b",
          borderRadius: "16px",
          border: "1px solid rgba(16, 185, 129, 0.3)",
          maxWidth: "560px",
          width: "100%",
          padding: "28px",
          boxShadow: "0 20px 25px -5px rgba(0,0,0,0.5)",
          color: "#f8fafc",
          position: "relative",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <span
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              padding: "4px 10px",
              borderRadius: "12px",
              backgroundColor: "rgba(16, 185, 129, 0.2)",
              color: "#34d399",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {current.badge} — Step {currentWalkthroughStep} of 7
          </span>

          <button
            onClick={stopWalkthrough}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              fontSize: "1.25rem",
              cursor: "pointer",
              padding: "4px",
            }}
          >
            &times;
          </button>
        </div>

        <h2 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 12px 0", color: "#f8fafc" }}>
          {current.title}
        </h2>

        <p style={{ fontSize: "0.95rem", color: "#cbd5e1", lineHeight: 1.6, margin: "0 0 16px 0" }}>
          {current.description}
        </p>

        <div
          style={{
            backgroundColor: "rgba(99, 102, 241, 0.1)",
            borderLeft: "4px solid #6366f1",
            padding: "12px 14px",
            borderRadius: "0 8px 8px 0",
            marginBottom: "24px",
            fontSize: "0.85rem",
            color: "#a5b4fc",
          }}
        >
          <strong>Interactive Action:</strong> {current.actionHint}
        </div>

        {/* Step dots */}
        <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginBottom: "24px" }}>
          {STEPS.map((s) => (
            <button
              key={s.step}
              onClick={() => setWalkthroughStep(s.step)}
              style={{
                width: s.step === currentWalkthroughStep ? "24px" : "8px",
                height: "8px",
                borderRadius: "4px",
                backgroundColor: s.step === currentWalkthroughStep ? "#10b981" : "#475569",
                border: "none",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            />
          ))}
        </div>

        {/* Controls */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button
            onClick={prevWalkthroughStep}
            disabled={currentWalkthroughStep === 1}
            style={{
              backgroundColor: "transparent",
              color: currentWalkthroughStep === 1 ? "#475569" : "#cbd5e1",
              border: "1px solid #475569",
              padding: "8px 16px",
              borderRadius: "8px",
              fontSize: "0.85rem",
              fontWeight: 500,
              cursor: currentWalkthroughStep === 1 ? "not-allowed" : "pointer",
            }}
          >
            Previous
          </button>

          {currentWalkthroughStep < 7 ? (
            <button
              onClick={nextWalkthroughStep}
              style={{
                backgroundColor: "#10b981",
                color: "#ffffff",
                border: "none",
                padding: "8px 20px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: "0 2px 8px rgba(16,185,129,0.3)",
              }}
            >
              Next Step &rarr;
            </button>
          ) : (
            <button
              onClick={stopWalkthrough}
              style={{
                backgroundColor: "#6366f1",
                color: "#ffffff",
                border: "none",
                padding: "8px 20px",
                borderRadius: "8px",
                fontSize: "0.85rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Finish Tour
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
