"use client";

import React, { useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { api } from "@/lib/api";
import { FileText, Download, Calendar, Filter, FileSpreadsheet, FileCode } from "lucide-react";

import { useDemo } from "@/context/DemoContext";

const REPORT_TYPES = [
  {
    id: "daily",
    label: "Power BI Executive & Date-Wise Daily Report",
    desc: "Strict date-specific performance report: exact 16-column CSV or comprehensive 9-section Power BI-style PDF",
  },
  { id: "dashboard", label: "Executive Dashboard Report", desc: "Overview KPI cards, data-source status, latest sensor readings" },
  { id: "energy", label: "Energy Consumption Report", desc: "Electricity usage statistics, peak demand, min/max metrics" },
  { id: "water", label: "Water Usage Report", desc: "Flow rate, pressure statistics, zone consumption" },
  { id: "waste", label: "Waste Generation Report", desc: "Solid waste volume, bin levels, compaction statistics" },
  { id: "environmental", label: "Environmental Quality Report", desc: "Temperature, humidity, CO₂ air quality monitoring" },
  { id: "anomalies", label: "Anomaly Detection Log", desc: "Recorded statistical outliers, severity levels, timestamps" },
  { id: "recommendations", label: "AI Recommendations Audit", desc: "Decision-support recommendations, target metrics, actions" },
  { id: "forecast", label: "AI/ML Forecast Report", desc: "Holt-Winters time-series predictions & 95% confidence bounds" },
  { id: "iot", label: "IoT Device Inventory Report", desc: "Registered microcontrollers, MAC addresses, status, firmware" },
];

export default function ReportsPage() {
  const { activeOrgId } = useAuth();
  const { showToast } = useToast();
  const { simulatedDate } = useDemo();

  const [selectedReport, setSelectedReport] = useState<string>("daily");
  const [format, setFormat] = useState<"csv" | "pdf">("pdf");
  const [selectedDate, setSelectedDate] = useState<string>(simulatedDate || "2026-09-20");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [downloading, setDownloading] = useState<boolean>(false);

  const handleDownload = async () => {
    if (!activeOrgId) {
      showToast("Organisation ID is required", "error");
      return;
    }

    setDownloading(true);
    showToast(`Generating ${selectedReport.toUpperCase()} report...`, "info");

    try {
      const params: Record<string, any> = {
        organisation_id: activeOrgId,
        format: format,
      };

      if (selectedReport === "daily") {
        params.date = selectedDate || simulatedDate || "2026-09-20";
      } else {
        if (startDate) params.start_date = startDate;
        if (endDate) params.end_date = endDate;
        if (selectedReport === "forecast") {
          params.sensor_type = "energy";
          params.horizon = "24h";
        }
      }

      const endpoint = selectedReport === "daily" ? "/api/v1/reports/daily" : `/api/v1/reports/${selectedReport}`;
      const { blob, filename } = await api.downloadReport(endpoint, params);

      // Trigger browser file download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showToast(`Downloaded ${filename}`, "success");
    } catch (err: any) {
      showToast(err.message || "Failed to download report", "error");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <AppLayout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 800, display: "flex", alignItems: "center", gap: "10px" }}>
            <FileText color="var(--clr-primary)" /> Reporting & Export Center
          </h1>
          <p style={{ fontSize: "14px", color: "var(--clr-text-secondary)" }}>
            Generate actual downloadable CSV spreadsheets and Power BI-style executive PDF documents
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px" }}>
        {/* Report Selection Grid */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "8px" }}>Select Report Type</h2>
          {REPORT_TYPES.map((r) => {
            const isSelected = selectedReport === r.id;
            return (
              <div
                key={r.id}
                onClick={() => setSelectedReport(r.id)}
                className="card"
                style={{
                  padding: "16px",
                  cursor: "pointer",
                  border: `2px solid ${isSelected ? "var(--clr-primary)" : "var(--clr-border)"}`,
                  background: isSelected ? "var(--clr-primary-light)" : "var(--clr-surface)",
                }}
              >
                <div style={{ fontWeight: 700, fontSize: "15px", color: isSelected ? "var(--clr-primary-dark)" : "var(--clr-text-primary)", marginBottom: "4px" }}>
                  {r.label}
                </div>
                <div style={{ fontSize: "13px", color: "var(--clr-text-secondary)" }}>{r.desc}</div>
              </div>
            );
          })}
        </div>

        {/* Export Configuration Form */}
        <div>
          <div className="card" style={{ padding: "24px", position: "sticky", top: "96px" }}>
            <h2 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "20px" }}>Export Configuration</h2>

            {/* Format Selection */}
            <div className="form-group">
              <label className="form-label">File Format</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <button
                  type="button"
                  onClick={() => setFormat("csv")}
                  className={`btn ${format === "csv" ? "btn-primary" : "btn-outline"}`}
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
                >
                  <FileSpreadsheet size={16} /> CSV Spreadsheet
                </button>
                <button
                  type="button"
                  onClick={() => setFormat("pdf")}
                  className={`btn ${format === "pdf" ? "btn-primary" : "btn-outline"}`}
                  style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
                >
                  <FileCode size={16} /> Power BI PDF
                </button>
              </div>
            </div>

            {/* Date Selection based on report type */}
            {selectedReport === "daily" ? (
              <div className="form-group">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                  <label className="form-label" style={{ margin: 0 }}>Target Simulated Date</label>
                  <button
                    type="button"
                    onClick={() => setSelectedDate(simulatedDate || "2026-09-20")}
                    style={{
                      fontSize: "11px",
                      color: "var(--clr-primary)",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      textDecoration: "underline",
                      padding: 0,
                    }}
                  >
                    Use Active Day ({simulatedDate || "2026-09-20"})
                  </button>
                </div>
                <input
                  type="date"
                  className="form-input"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                />
                <span style={{ fontSize: "12px", color: "var(--clr-text-muted)", display: "block", marginTop: "4px" }}>
                  {format === "csv"
                    ? "Generates strict 16-column date-wise CSV matching the selected date."
                    : "Generates comprehensive 9-section Power BI-style PDF report for the selected date."}
                </span>
              </div>
            ) : (
              <>
                <div className="form-group">
                  <label className="form-label">Start Date (Optional)</label>
                  <input
                    type="date"
                    className="form-input"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">End Date (Optional)</label>
                  <input
                    type="date"
                    className="form-input"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </>
            )}

            {/* Organisation Badge */}
            <div style={{ background: "var(--clr-surface-2)", padding: "12px 16px", borderRadius: "8px", fontSize: "13px", color: "var(--clr-text-secondary)", marginBottom: "24px" }}>
              Target Organisation: <strong>{activeOrgId}</strong>
            </div>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="btn btn-primary btn-lg"
              style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}
            >
              <Download size={18} />
              <span>{downloading ? "Generating File..." : `Download ${selectedReport === "daily" && format === "pdf" ? "Power BI PDF" : format.toUpperCase()}`}</span>
            </button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
