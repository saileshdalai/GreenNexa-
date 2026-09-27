/**
 * GreenNexa — Dashboard Style System (frontend) unit tests.
 *
 * Runs with the built-in Node test runner (no test framework required):
 *   node --test tests/dashboard-style.test.mjs
 *
 * These cover the pure modules that drive every dashboard style: the style
 * registry, style normalisation, the per-organisation cache, the section plan
 * resolution (so no style can fabricate a module it has no data for) and the
 * shared view model (so switching style provably cannot change data).
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  DASHBOARD_STYLES,
  DASHBOARD_STYLE_VALUES,
  DEFAULT_DASHBOARD_STYLE,
  cacheDashboardStyle,
  composeRows,
  dashboardStyleStorageKey,
  getKpiEmphasis,
  getSectionVariant,
  getStyleDefinition,
  isDashboardStyle,
  normaliseDashboardStyle,
  readCachedDashboardStyle,
  resolveSections,
} from "../src/lib/dashboardStyles.ts";

import {
  buildDashboardViewModel,
  normaliseAnomalies,
  normaliseRecommendations,
  pickAnalyticsMetric,
} from "../src/components/dashboard/dashboardViewModel.ts";

const ALL_CAPABILITIES = {
  hasKpis: true,
  hasAnomalies: true,
  hasRecommendations: true,
  hasForecast: true,
  hasTrend: true,
  hasRecentReadings: true,
  hasWards: true,
  hasModules: true,
  hasAssociatedOrgs: true,
  isMunicipality: true,
};

const ALL_SECTIONS = [
  "health-summary",
  "kpis",
  "critical-alerts",
  "insights",
  "forecast",
  "anomalies",
  "recommendations",
  "quick-actions",
  "recent-activity",
  "analytics-metrics",
  "analytics-trend",
  "modules",
  "ward-status",
  "spatial-overview",
  "associated-orgs",
];

/** @type {string[]} */
const ALL_SECTION_LIST = ALL_SECTIONS;

function fakeStorage(initial = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (key) => (map.has(key) ? map.get(key) : null),
    setItem: (key, value) => void map.set(key, value),
    _dump: () => Object.fromEntries(map),
  };
}

/* ------------------------------------------------------------------ */
/* 1. Registry: exactly four selectable styles                          */
/* ------------------------------------------------------------------ */

test("registry exposes exactly the four supported styles", () => {
  assert.deepEqual([...DASHBOARD_STYLE_VALUES], ["EXECUTIVE", "OPERATIONS", "ANALYTICS", "COMMAND_CENTER"]);
  assert.equal(DASHBOARD_STYLES.length, 4);
  assert.deepEqual(
    DASHBOARD_STYLES.map((s) => s.id),
    [...DASHBOARD_STYLE_VALUES]
  );
  for (const style of DASHBOARD_STYLES) {
    assert.ok(style.label.length > 0, `${style.id} needs a label`);
    assert.ok(style.tagline.length > 0, `${style.id} needs a tagline`);
    assert.ok(style.description.length > 20, `${style.id} needs a real description`);
    assert.ok(style.audience.length > 0, `${style.id} needs an audience`);
    assert.ok(style.sections.length >= 4, `${style.id} needs a composition`);
    assert.ok(style.preview.cells.length > 0, `${style.id} needs a preview thumbnail`);
    assert.equal(
      style.sections[0],
      style.leadSection,
      `${style.id} lead section must be the first composed section`
    );
  }
});

test("default style is EXECUTIVE and unknown styles fall back to it", () => {
  assert.equal(DEFAULT_DASHBOARD_STYLE, "EXECUTIVE");
  assert.equal(getStyleDefinition("nope").id, "EXECUTIVE");
  assert.equal(getStyleDefinition(undefined).id, "EXECUTIVE");
  assert.equal(getStyleDefinition(null).id, "EXECUTIVE");
  assert.equal(getStyleDefinition(42).id, "EXECUTIVE");
});

/* ------------------------------------------------------------------ */
/* 2. Selection tolerance                                              */
/* ------------------------------------------------------------------ */

test("style values validate and normalise with light formatting tolerance", () => {
  assert.equal(isDashboardStyle("OPERATIONS"), true);
  assert.equal(isDashboardStyle("operations"), false);
  assert.equal(isDashboardStyle(3), false);

  assert.equal(normaliseDashboardStyle("EXECUTIVE"), "EXECUTIVE");
  assert.equal(normaliseDashboardStyle(" executive "), "EXECUTIVE");
  assert.equal(normaliseDashboardStyle("Command_Center"), "COMMAND_CENTER");
  assert.equal(normaliseDashboardStyle("Command Center"), "COMMAND_CENTER");
  assert.equal(normaliseDashboardStyle("command-center"), "COMMAND_CENTER");
  // Anything outside the allowed set is never invented — it falls back to default.
  assert.equal(normaliseDashboardStyle("commandcentre"), "EXECUTIVE");
  assert.equal(normaliseDashboardStyle("totally-unknown"), "EXECUTIVE");
  assert.equal(normaliseDashboardStyle(undefined), "EXECUTIVE");
});

/* ------------------------------------------------------------------ */
/* 3. Persistence is per organisation                                   */
/* ------------------------------------------------------------------ */

test("cached style is stored per organisation and never leaks across orgs", () => {
  const storage = fakeStorage();

  cacheDashboardStyle(storage, "ORG-A", "ANALYTICS");
  cacheDashboardStyle(storage, "ORG-B", "COMMAND_CENTER");

  assert.equal(readCachedDashboardStyle(storage, "ORG-A"), "ANALYTICS");
  assert.equal(readCachedDashboardStyle(storage, "ORG-B"), "COMMAND_CENTER");
  assert.equal(readCachedDashboardStyle(storage, "ORG-C"), null);

  assert.notEqual(dashboardStyleStorageKey("ORG-A"), dashboardStyleStorageKey("ORG-B"));
  assert.deepEqual(Object.keys(storage._dump()).sort(), [
    "greennexa_dashboard_style:ORG-A",
    "greennexa_dashboard_style:ORG-B",
  ]);
});

test("cache reads are tolerant of stored junk and unavailable storage", () => {
  const storage = fakeStorage({ "greennexa_dashboard_style:ORG-X": "bogus-value" });
  assert.equal(readCachedDashboardStyle(storage, "ORG-X"), "EXECUTIVE");
  assert.equal(readCachedDashboardStyle(null, "ORG-X"), null);
  assert.equal(readCachedDashboardStyle(storage, ""), null);

  const broken = {
    getItem() {
      throw new Error("blocked");
    },
    setItem() {
      throw new Error("blocked");
    },
  };
  assert.equal(readCachedDashboardStyle(broken, "ORG-X"), null);
  assert.doesNotThrow(() => cacheDashboardStyle(broken, "ORG-X", "ANALYTICS"));
  assert.doesNotThrow(() => cacheDashboardStyle(null, "ORG-X", "ANALYTICS"));
});

/* ------------------------------------------------------------------ */
/* 4. Styles are genuinely different layouts                            */
/* ------------------------------------------------------------------ */

test("each style composes a distinct section order", () => {
  const orders = DASHBOARD_STYLES.map((s) => s.sections.join(">"));
  assert.equal(new Set(orders).size, DASHBOARD_STYLES.length, "styles must not share an identical order");
});

test("every style keeps the shared core panels when data exists", () => {
  for (const style of DASHBOARD_STYLE_VALUES) {
    const sections = resolveSections(style, ALL_CAPABILITIES);
    assert.ok(sections.includes("kpis"), `${style} must show KPIs`);
    assert.ok(sections.includes("anomalies"), `${style} must show anomalies`);
    assert.ok(sections.includes("recommendations"), `${style} must show recommendations`);
    assert.ok(sections.includes("quick-actions"), `${style} must show quick actions`);
  }
});

test("every style can render every panel — they differ only in order and emphasis", () => {
  const shared = resolveSections("EXECUTIVE", ALL_CAPABILITIES);
  for (const style of DASHBOARD_STYLE_VALUES) {
    const sections = resolveSections(style, ALL_CAPABILITIES);
    assert.deepEqual(
      [...sections].sort(),
      [...shared].sort(),
      `${style} must expose the same complete panel set as the default style`
    );
  }
});

test("row packing produces different compositions per style", () => {
  const municipality = { ...ALL_CAPABILITIES, isMunicipality: true };
  const executive = composeRows(resolveSections("EXECUTIVE", municipality), { shareRow: ALL_SECTION_LIST, groupSize: 2 });
  const command = composeRows(resolveSections("COMMAND_CENTER", municipality), { shareRow: ALL_SECTION_LIST, groupSize: 3 });

  assert.equal(executive.flat().length, resolveSections("EXECUTIVE", municipality).length);
  assert.equal(command.flat().length, resolveSections("COMMAND_CENTER", municipality).length);
  assert.notDeepEqual(executive, command, "grouping must differ between styles");
  assert.ok(executive.some((row) => row.length === 2));
  assert.ok(command.some((row) => row.length === 3));
  assert.ok(executive.every((row) => row.length >= 1 && row.length <= 2));
  assert.ok(command.every((row) => row.length >= 1 && row.length <= 3));
});

test("row packing keeps trailing panels and full-width sections intact", () => {
  // A trailing partial group still renders.
  assert.deepEqual(
    composeRows(["kpis", "anomalies", "recommendations", "modules"], { shareRow: ALL_SECTION_LIST, groupSize: 3 }),
    [["kpis", "anomalies", "recommendations"], ["modules"]]
  );
  // Non-shareable sections (health strip, KPI grid) always own their row.
  assert.deepEqual(
    composeRows(["health-summary", "critical-alerts", "insights"], { shareRow: ["critical-alerts", "insights"], groupSize: 2 }),
    [["health-summary"], ["critical-alerts", "insights"]]
  );
  assert.deepEqual(composeRows([], { shareRow: ALL_SECTION_LIST }), []);
});

test("style-specific emphasis and panel variants differ per style", () => {
  const emphases = DASHBOARD_STYLES.map((s) => getKpiEmphasis(s.id));
  assert.deepEqual(emphases, ["hero", "dense", "table", "radial"]);
  assert.equal(getSectionVariant("EXECUTIVE", "anomalies"), "critical");
  assert.equal(getSectionVariant("OPERATIONS", "anomalies"), "priority");
  assert.equal(getSectionVariant("ANALYTICS", "anomalies"), "trend");
  assert.equal(getSectionVariant("COMMAND_CENTER", "anomalies"), "critical");
  assert.equal(getSectionVariant("OPERATIONS", "recommendations"), "actions");
  assert.equal(getSectionVariant("ANALYTICS", "recommendations"), "table");
  assert.equal(getSectionVariant("EXECUTIVE", "kpis"), "summary");
});

/* ------------------------------------------------------------------ */
/* 5. No style may fabricate modules it has no data for                 */
/* ------------------------------------------------------------------ */

test("sections without data are dropped for every style", () => {
  const noData = {
    hasKpis: false,
    hasAnomalies: false,
    hasRecommendations: false,
    hasForecast: false,
    hasTrend: false,
    hasRecentReadings: false,
    hasWards: false,
    hasModules: false,
    hasAssociatedOrgs: false,
    isMunicipality: false,
  };

  for (const style of DASHBOARD_STYLE_VALUES) {
    const sections = resolveSections(style, noData);
    assert.deepEqual(
      sections,
      ["quick-actions"],
      `${style} must only keep pure navigation chrome when there is no data`
    );
  }
});

test("partial data only enables the sections that can be filled", () => {
  const kpisOnly = { ...ALL_CAPABILITIES, hasAnomalies: false, hasForecast: false, hasTrend: false, hasWards: false };

  for (const style of DASHBOARD_STYLE_VALUES) {
    const sections = resolveSections(style, kpisOnly);
    assert.ok(sections.includes("kpis"));
    assert.ok(!sections.includes("anomalies"), `${style} must not fabricate anomalies`);
    assert.ok(!sections.includes("critical-alerts"), `${style} must not fabricate critical alerts`);
    assert.ok(!sections.includes("forecast"), `${style} must not fabricate a forecast`);
    assert.ok(!sections.includes("analytics-trend"), `${style} must not fabricate a trend`);
    assert.ok(!sections.includes("ward-status"), `${style} must not fabricate wards`);
  }
});

test("municipality-only sections appear only for municipalities with data", () => {
  const municipality = { ...ALL_CAPABILITIES, isMunicipality: true };
  const facility = { ...ALL_CAPABILITIES, isMunicipality: false };

  const commandMuni = resolveSections("COMMAND_CENTER", municipality);
  assert.ok(commandMuni.includes("spatial-overview"));
  assert.ok(commandMuni.includes("ward-status"));

  const commandFacility = resolveSections("COMMAND_CENTER", facility);
  assert.ok(!commandFacility.includes("ward-status"));
  assert.ok(!commandFacility.includes("associated-orgs"));
});

test("unknown style resolves to the default plan", () => {
  assert.deepEqual(resolveSections("nope", ALL_CAPABILITIES), resolveSections("EXECUTIVE", ALL_CAPABILITIES));
});

/* ------------------------------------------------------------------ */
/* 6. The view model is style-independent                               */
/* ------------------------------------------------------------------ */

const SAMPLE_INPUT = {
  organisationId: "ORG-STYLE-A",
  organisationName: "Style Test Facility",
  isMunicipality: false,
  score: { value: 90, label: "OPTIMAL", color: "#22c55e" },
  kpis: {
    energy: { unit: "kWh", latest_value: 128.4, average: 120, minimum: 90, maximum: 160, reading_count: 48, is_anomaly: false },
    water: { unit: "L", latest_value: 950, average: 900, minimum: 700, maximum: 1200, reading_count: 48, is_anomaly: true, anomaly_severity: "HIGH" },
  },
  anomalies: [
    { id: "a1", metric: "water", severity: "HIGH", status: "OPEN", value: 1500, unit: "L", timestamp: "2026-09-20T10:00:00Z" },
    { id: "a2", metric: "energy", severity: "CRITICAL", status: "OPEN", value: 220, unit: "kWh", timestamp: "2026-09-20T10:05:00Z" },
    { id: "a3", metric: "waste", severity: "LOW", status: "OPEN", value: 12, unit: "kg", timestamp: "2026-09-20T10:06:00Z" },
  ],
  recommendations: [
    { id: "r1", metric: "energy", summary: "Shift the HVAC schedule", priority: "HIGH", status: "OPEN", recommended_actions: ["Lower setpoint by 2C"] },
    { id: "r2", metric: "water", summary: "Fix the leaking valve", priority: "LOW", status: "DONE", recommended_actions: ["Seal valve"] },
  ],
  recentReadings: [
    { id: "rd1", sensor_type: "energy", value: 128.4, unit: "kWh", source: "synthetic", timestamp: "2026-09-20T10:00:00Z", is_anomaly: false },
  ],
  forecast: { metric: "energy", unit: "kWh", available: true, points: [{ timestamp: "2026-09-20T11:00:00Z", predicted_value: 130 }] },
  trend: { metric: "energy", unit: "kWh", available: true, points: [{ timestamp: "2026-09-20T09:00:00Z", value: 120, is_anomaly: false }, { timestamp: "2026-09-20T10:00:00Z", value: 128, is_anomaly: false }] },
};

test("view model never carries a style — the style cannot change data", () => {
  const vm = buildDashboardViewModel(SAMPLE_INPUT);
  assert.equal("style" in vm, false);
  assert.equal("dashboard_style" in vm, false);
  assert.equal(DASHBOARD_STYLES.length, 4, "styles exist, but the view model is style agnostic");
});

test("view model is deterministic and does not mutate its input", () => {
  const snapshot = JSON.stringify(SAMPLE_INPUT);
  const first = buildDashboardViewModel(SAMPLE_INPUT);
  const second = buildDashboardViewModel(SAMPLE_INPUT);

  assert.deepEqual(first, second, "building the view model twice must produce identical data");
  assert.equal(JSON.stringify(SAMPLE_INPUT), snapshot, "the source payload must not be mutated");
});

test("view model normalises KPIs, anomalies and recommendations from raw payloads", () => {
  const vm = buildDashboardViewModel(SAMPLE_INPUT);

  assert.deepEqual(
    vm.kpis.map((k) => k.key),
    ["energy", "water"]
  );
  assert.equal(vm.kpis[0].title, "Energy Consumption");
  assert.equal(vm.kpis[1].title, "Water Usage");
  assert.equal(vm.kpis[0].displayValue, "128.4");
  assert.ok(vm.kpis[0].trendPct > 0, "deviation from the average is derived");
  assert.equal(vm.kpis[1].status, "warning", "an anomalous KPI is flagged");

  assert.deepEqual(
    vm.anomalies.map((a) => a.severity),
    ["CRITICAL", "HIGH", "LOW"],
    "anomalies are ordered by severity"
  );
  assert.equal(vm.anomalies[0].metric, "energy");

  assert.equal(vm.recommendations.length, 1, "only open/active recommendations are kept");
  assert.equal(vm.recommendations[0].priority, "HIGH");
  assert.deepEqual(vm.recommendations[0].actions, ["Lower setpoint by 2C"]);
});

test("capabilities describe exactly the data that exists", () => {
  const vm = buildDashboardViewModel(SAMPLE_INPUT);
  assert.equal(vm.capabilities.hasKpis, true);
  assert.equal(vm.capabilities.hasAnomalies, true);
  assert.equal(vm.capabilities.hasRecommendations, true);
  assert.equal(vm.capabilities.hasForecast, true);
  assert.equal(vm.capabilities.hasTrend, true);
  assert.equal(vm.capabilities.hasRecentReadings, true);
  assert.equal(vm.capabilities.hasWards, false);
  assert.equal(vm.capabilities.hasModules, false);
  assert.equal(vm.capabilities.isMunicipality, false);

  const empty = buildDashboardViewModel({ organisationId: "ORG-EMPTY" });
  for (const [key, value] of Object.entries(empty.capabilities)) {
    if (key === "isMunicipality") assert.equal(value, false);
    else assert.equal(value, false, `${key} must be false without data`);
  }
  assert.deepEqual(empty.kpis, []);
  assert.deepEqual(empty.anomalies, []);
  assert.deepEqual(empty.recommendations, []);
  assert.deepEqual(resolveSections("ANALYTICS", empty.capabilities), ["quick-actions"]);
});

test("forecast and trend are optional and never invented", () => {
  const vm = buildDashboardViewModel({ organisationId: "ORG-NO-FORECAST", kpis: SAMPLE_INPUT.kpis });
  assert.equal(vm.forecast.available, false);
  assert.deepEqual(vm.forecast.points, []);
  assert.equal(vm.forecast.message.length > 0, true);
  assert.equal(vm.trend.available, false);
  assert.deepEqual(vm.trend.points, []);

  const partial = buildDashboardViewModel({
    organisationId: "ORG-PARTIAL",
    kpis: SAMPLE_INPUT.kpis,
    trend: { metric: "energy", unit: "kWh", available: true, points: SAMPLE_INPUT.trend.points },
  });
  assert.equal(partial.trend.available, true);
  assert.equal(partial.forecast.available, false, "a trend must not imply a forecast");
  assert.equal(resolveSections("ANALYTICS", partial.capabilities).includes("forecast"), false);
});

test("malformed payloads degrade to empty data instead of throwing", () => {
  const vm = buildDashboardViewModel({
    organisationId: "ORG-BROKEN",
    kpis: null,
    anomalies: "not-an-array",
    recommendations: undefined,
    recentReadings: null,
    wards: "nope",
    associatedOrgs: 5,
    forecast: { metric: "energy", available: true, points: "nope" },
    trend: { metric: "energy", available: true, points: null },
  });
  assert.deepEqual(vm.kpis, []);
  assert.deepEqual(vm.anomalies, []);
  assert.deepEqual(vm.recommendations, []);
  assert.deepEqual(vm.recentReadings, []);
  assert.deepEqual(vm.wards, []);
  assert.deepEqual(vm.associatedOrgs, []);
  assert.equal(vm.forecast.available, false);
  assert.equal(vm.trend.available, false);
  assert.equal(vm.organisationName, "ORG-BROKEN");
});

test("normalisers tolerate alternative API payload shapes", () => {
  assert.deepEqual(normaliseAnomalies({ items: [{ id: "1", metric: "energy", severity: "low" }] })[0].metric, "energy");
  assert.deepEqual(normaliseAnomalies(null), []);
  assert.equal(normaliseRecommendations([{ id: "1", summary: "Do it", status: "CLOSED" }]).length, 0);
  assert.equal(normaliseRecommendations([{ id: "2", summary: "Do it", status: "ACTIVE" }]).length, 1);
});

test("municipality view model derives ward status from the same anomalies", () => {
  const vm = buildDashboardViewModel({
    organisationId: "ORG-MUNI",
    isMunicipality: true,
    wards: [
      { id: "W1", ward_number: "1", ward_name: "Ward One" },
      { id: "W2", ward_number: "2", ward_name: "Ward Two" },
    ],
    anomalies: [
      { id: "a1", metric: "water", severity: "CRITICAL", status: "OPEN", ward_id: "W1" },
      { id: "a2", metric: "waste", severity: "HIGH", status: "OPEN", ward_id: "W2" },
    ],
    isWardUnread: (id) => id === "W2",
  });

  assert.equal(vm.wards.length, 2);
  assert.equal(vm.wards[0].status, "critical");
  assert.equal(vm.wards[0].alertsCount, 1);
  assert.equal(vm.wards[1].status, "warning");
  assert.equal(vm.wards[1].hasUnread, true);
  assert.equal(vm.wards[0].hasUnread, false);
  assert.equal(vm.scope, "municipality");
  assert.equal(vm.capabilities.hasWards, true);
});

test("quick actions adapt to the organisation scope", () => {
  const facility = buildDashboardViewModel({ organisationId: "ORG-F", isMunicipality: false });
  const municipality = buildDashboardViewModel({
    organisationId: "ORG-M",
    isMunicipality: true,
    wards: [{ id: "W1", ward_number: "1", ward_name: "Ward One" }],
  });

  assert.equal(facility.quickActions.some((a) => a.id === "wards"), false);
  assert.equal(municipality.quickActions.some((a) => a.id === "wards"), true);
  assert.ok(facility.quickActions.every((a) => a.href.startsWith("/")));
});

/* ------------------------------------------------------------------ */
/* 7. Analytics metric choice is deterministic and style independent     */
/* ------------------------------------------------------------------ */

test("analytics metric selection is deterministic and preference based", () => {
  assert.equal(pickAnalyticsMetric(["waste", "energy", "water"]), "energy");
  assert.equal(pickAnalyticsMetric(["waste", "water"]), "water");
  assert.equal(pickAnalyticsMetric(["waste"]), "waste");
  assert.equal(pickAnalyticsMetric([" Waste ", "Climate"]), "waste");
  assert.equal(pickAnalyticsMetric([]), null);
  assert.equal(pickAnalyticsMetric(["waste", "energy"]), pickAnalyticsMetric(["energy", "waste"]));
});
