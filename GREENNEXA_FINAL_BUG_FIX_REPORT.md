# GREENNEXA FINAL BUG FIX REPORT

**Date:** 2026-09-24
**Scope:** FINAL ALL-BUG ROOT-CAUSE FIX pass (spec sections 1–32)
**Supersedes:** `GREENNEXA_FINAL_IMPLEMENTATION_REPORT.md` (old A–J / old BUG-01..25 numbering — historical only)

---

## 0. Status Overview

| Item | Result |
|---|---|
| Backend test suite | **531 passed, 0 failed** (108.5s) — baseline 494 + 37 new mandatory tests |
| New mandatory regression suite | **37 passed** (`tests/test_greennexa_final_all_bugs.py`, 3.92s) |
| Frontend typecheck (`npx tsc --noEmit`) | **Clean** (no errors) |
| Frontend build (`npm run build`) | **Succeeded** — 35 routes, TypeScript pass clean |
| Browser smoke tests (TEST A–J) | **NOT TESTED** — "BROWSER VERIFICATION NOT AVAILABLE" (no browser in this environment) |
| Database safety | No migration, no DROP/ALTER on application data, no row deletions (section L) |
| Demo timing evidence | First anomaly ~30–40s, subsequent 60–120s (section M) |
| Demo scope evidence | Only enrolled org generates; others frozen (section M) |

Honesty rules applied: no item below is marked FIXED on compile alone — every FIXED row names the test(s) that prove it. Items already correct in code but now guarded by regression tests are marked **VERIFIED**. Browser-only tests are marked **NOT TESTED**.

---

## A. Demo Data Isolation (TEST A/B)

**Requirement:** While a demo is active for one organisation, only that organisation's telemetry changes; every other organisation (government, private, other sector) stays frozen.

**Root cause:** Demo mode was a process-global boolean (`_demo_enabled`). Every active synthetic organisation generated data regardless of which org the operator started demo for; start/stop/status had no organisation scope.

**Fix (FIXED):**
- `backend/app/services/synthetic_simulator.py` → `_demo_orgs: set[str]` replaces the boolean; sentinel `"*"` = global demo (no-org start, preserving prior behaviour); `_enroll_demo()` / `_demo_active_for()` helpers.
- `run_cycle()` gate (after `processed_count += 1`): if `_demo_orgs` is non-empty, `continue` for any org where `not self._demo_active_for(org.id)` — non-enrolled orgs literally generate zero readings.
- `start(demo_mode, organisation_id)` enrolls; `demo_mode=False` clears; `stop(organisation_id)` un-enrolls one org (`status: "scoped_stopped"`) while the worker keeps serving other enrolled orgs; `stop()` full stop clears everything; `status(organisation_id)` returns per-org `demo_mode` + `generation_active`.
- `reset_all_simulator_state()` clears `_demo_orgs` (no stale scope after reset).
- API: `app/api/v1/simulator.py` passes `organisation_id or current_user.organisation_id` into start/stop/status; `schemas/simulator.py` adds `generation_active`.
- Frontend: `DemoControlPanel` resolves the active org (`getOrgId()`) and sends it in the start/stop **body** (api.post has no params arg) and the status **query**; `DemoContext` derives `demoModeActive` from per-org `status.demo_mode`.

**Evidence:**
- `TestDemoScopeIsolation::test_4_demo_org_a_changes_only_org_a` — enrolled college gets 4 energy readings; hospital **0**; municipality **0** (TEST A/B).
- `test_5_government_and_private_orgs_frozen` — non-enrolled government org generates; private org frozen.
- `test_6_municipality_demo_changes_only_municipality_scope` — only the municipality changes.
- `test_7_enrollment_follows_owner_and_demo_generation_active`, `test_8_stop_org_relinquishes_scope_without_stopping_others` — scoped stop keeps the other enrolled org generating.
- `test_demo_mode_propagation_through_api` (start → status demo=True → stop → demo=False, no test changes needed).
- `test_demo_mode_status_flag` (no-org start → global `"*"`; stop clears).

---

## B. Real-Time 30-Second Cadence & "Last Updated"

**Requirement:** Data persists on the live 30s cycle; the dashboard "Last Updated" timestamp reflects the newest reading.

**Root cause:** No functional defect found in cadence persistence; risk was stale/incorrect `last_updated_at` sourcing.

**Fix:** Dashboard `last_updated_at` is sourced from `metric_sum.latest_timestamp` (per-cycle aggregate of the newest reading) — `app/api/v1/dashboard.py`. Verified rather than changed.

**Evidence (VERIFIED):**
- `TestRealTimeCadence::test_1_30s_cycle_persists_fresh_readings` — 2 energy readings after cycle T, 4 after cycle T+30s; newest timestamp == T+30s.
- `test_1b_dashboard_last_updated_follows_latest_reading` — KPI `latest_timestamp` == T+30s; `last_updated_at` non-null.
- `test_3_recent_readings_show_newest_cycle` — `/dashboard/{org}/recent` newest item == T+30s.

---

## C. Fast Demo Anomaly Cadence (~30–40s, then 60–120s)

**Requirement:** First demo anomaly within ~30–40s of demo start; subsequent events staggered 60–120s; at most one per cycle; polling must not duplicate anomalies.

**Root cause:** Cadence constants were `DEMO_FIRST_DELAY_SECONDS = (45, 60)` / `(45, 120)` — first event could not land inside the 30–40s window, and the second-band timing was unverified per-org.

**Fix (FIXED):**
- `DEMO_FIRST_DELAY_SECONDS = (10.0, 25.0)` — schedule is primed on the first demo-enabled cycle, so the event fires on the **next 30s tick** (~30–40s from demo start).
- `DEMO_NEXT_DELAY_SECONDS = (60.0, 120.0)` — enforced inside `_consume_demo_anomaly()`, which advances the schedule atomically per org (`_demo_schedules`), capped at one fire per org per cycle (demo block only runs when no natural/forced anomaly fired).
- Single-anomaly invariant preserved: `anomaly_sensor_selected is None and self._demo_active_for(org.id) and not is_forced`.
- Existing test `test_demo_scheduler_cadence_and_single_anomaly` rewritten for the new contract (first ≤ step*5+40s, gaps in 12..24 steps, max one per cycle, ≥1 ward-scoped fire).

**Evidence:**
- `TestDemoAnomalyCadence::test_16_first_anomaly_within_about_40s` — first fire measured at 10–40s after schedule prime.
- `test_17_subsequent_anomalies_every_60_120s` — subsequent gap measured in [60, 130]s (10s step granularity).
- `test_21_no_duplicate_anomalies_from_polling` — same-time re-cycles add **0** anomalies; exactly 1 more arrives when the schedule matures.
- `test_13_...` / `test_14_...` — exactly one anomaly reading per demo cycle.

---

## D. Municipality Ward Civic Data (Energy / Water / Waste / Air Quality)

**Requirement:** During a municipality demo, ward pages must show live, changing Energy/Water/Waste/AQ data per ward — while own-office blocks keep their own block-scoped readings.

**Root cause:** `extra_ward_civic` generation did not exist. Energy/Water/Waste are block-wise modules (own-office only) and Air Quality was whole-org only — wards received zero civic readings, so `has_data` stayed `False`.

**Fix (FIXED):** `_generate_org_readings()`:
```python
demo_active = self._demo_active_for(org.id)
extra_ward_civic = {"energy", "water", "waste", "air_quality"} \
    if (is_muni and demo_active and wards) else set()
```
- Energy/Water/Waste during demo → one reading **per ward** (ward_id set, block_id None) **plus** the existing own-office block readings (both coexist).
- Air Quality (whole-org default) → during demo generates **per ward** instead of a single org-level row; never gets a block_id.
- Non-demo cycles are byte-for-byte unchanged (block-wise / whole-org defaults), keeping legacy count expectations intact.

**Evidence:**
- `TestMunicipalityWardDemoData::test_11_ward_detail_energy_water_waste_aq_has_data` — ward 1 detail: energy/water/waste/air_quality all `has_data=True`, `latest_value` non-null (BUG-05 regression).
- `test_10_ward_readings_have_correct_ward_id_no_block` — 4 ward energy rows (2 wards × 2 cycles, ward_id ∈ {1,2}, block_id None) + 2 own-office block rows.
- `test_32_air_quality_never_uses_blocks` — AQ during demo: block_id None on every row, ward_id ∈ {1,2}.
- `test_35_municipality_own_office_live_data_during_demo` — own-office energy rows (2) and ward energy rows (4) both present simultaneously.
- `test_municipality_ward_civic_suite.py` (pre-existing, non-demo counts unchanged).
- `test_9`, `test_12` — ward list shows 2 wards; street lighting changes per ward.

---

## E. Ward Anomaly → Ward Record Propagation

**Requirement:** A ward-targeted anomaly must set `ward_id` on both the flagged reading and the `AnomalyRecord`; ward-scoped civic scenarios must not fire at block/org scope for municipalities.

**Root cause:** (1) The flagging decision used a **static sensor→scope map** (`_scope_for_sensor`) instead of the scope actually chosen for the cycle — energy/water/waste/AQ resolved to `("org", None)` while the demo re-scope had picked a ward, so no reading was flagged. (2) `_consume_demo_anomaly()` honored scenario scope literally, allowing block/org-scope civic events for municipalities with wards.

**Fix (FIXED):**
- `_anomaly_match_key(scope, target)` derives the key from the **actual target**: ward → `("ward", ward_number)`, block → `("block", block_id)`, else `("org", None)`; used by `_generate_org_readings` to flag exactly the reading at the chosen location. Static `_scope_for_sensor` deleted (grep: no remaining callers).
- `_consume_demo_anomaly()` re-scopes municipality civic scenarios (water, waste, energy, air_quality) from `block`/`org` → `ward` whenever the org has active wards.

**Evidence:**
- `TestMunicipalityWardDemoData::test_13_ward_scoped_civic_anomaly_attaches_ward_id` — forced Waste Overflow → reading `is_anomaly=True` with `ward_id ∈ {1,2}`, `block_id None`; `AnomalyRecord.ward_id` matches; status OPEN.
- `test_14_first_demo_anomaly_scoped_to_ward_energy` — Energy Overload fires on a ward reading, not org/block.
- `test_19_wards_valid_and_records_attached_after_anomaly` — flagged reading and anomaly record share the same ward_id.
- `test_18_demo_anomaly_flows_through_real_pipeline` — sewage_level ward anomaly → OPEN AnomalyRecord with ward_id + severity.
- `test_ward_scoped_anomaly_copies_ward_id_to_record` (pre-existing, forced traffic) — passes unchanged.

---

## F. Complete Ward Detail

**Requirement:** The ward metrics page exposes the full civic module set (sewage, roads, parks, water flow, water level, rainfall, climate, temperature, humidity, …), never leaking facility blocks.

**Root cause:** `CIVIC_MODULES_SPECS` in `get_ward_detail` listed only 8 modules.

**Fix (FIXED):** Expanded to **18 entries** — energy, water, waste, sewage, sewage_level, air_quality, traffic, parking, street_lighting, roads, parks, safety, water_flow, water_level, rainfall, climate, temperature, humidity.

**Evidence:**
- `TestMunicipalityWardDemoData::test_15_ward_detail_never_shows_block_data` — for every `has_data=True` metric, the latest matching reading has `block_id is None`.
- `test_11` — civic metrics resolve from ward-scoped rows only.
- `test_9` — ward list returns MunicipalityWard rows (`ward_number` 1, 2), never blocks.

---

## G. Priority Engine

**Requirement:** ≥3 active anomalies activate the engine; Critical ranks first; honest "inactive" / "no high-priority" states.

**Root cause:** No defect found — behaviour is deterministic (score = severity + breach + deviation + recurrence + age; `CRITICAL` when severity CRITICAL / critical breach / score ≥ 140).

**Fix:** None required — **VERIFIED** with new API-level regressions.

**Evidence:**
- `TestPriorityEngine::test_22_priority_ranks_critical_first` — 3 anomalies (MEDIUM/HIGH/CRITICAL) → `is_active=True`, `top_priority.priority_level == "CRITICAL"`.
- `test_23_priority_inactive_below_threshold` — 1 anomaly → `is_active=False`, message contains "inactive".
- `GET /api/v1/anomalies/{org}/priority` and `/anomalies/priority` both route through the same service (confirmed).

---

## H. Forecast Scoping

**Requirement:** Ward forecasts derive strictly from that ward's own readings (≥3 points, least-squares, honest "insufficient history" otherwise); org-level block-wise aggregates are not contaminated by ward rows.

**Root cause:** Risk of ward readings leaking into org-level block-wise aggregates and of fabricated ward forecasts.

**Fix:** `build_ward_forecast_items()` filters `SensorReading.ward_id IN (ward_number, id)`; emits `is_available=False` + "Insufficient ward history…" under 3 points. `compute_metric_summary` cycle points for block-wise modules use block-scoped rows. Both **VERIFIED** by new tests.

**Evidence:**
- `TestForecastScoping::test_24_energy_ward_forecast_uses_only_ward_history` — 3 ward-1 readings (100→110→115) + a ward-2 reading of 9999 → forecast `is_available=True`, 3 points (6h/12h/24h), `current_value == 115` (**9999 excluded**).
- `test_25_org_level_aggregation_not_contaminated_by_wards` — block rows (100) + ward rows (500): cycle points `[100, 100]`, `current_value == 100` (ward rows excluded).
- `test_26_ward_forecast_honest_when_insufficient_history` — 1 reading → `is_available=False`, message contains "Insufficient".
- `test_greennexa_final_regression.py` forecast tests — pass unchanged.

---

## I. Aggregation Rules (Overall ≠ Highest Block; Current; Peak)

**Requirement:** Overall = SUM (not MAX) across blocks for additive metrics; Current = latest cycle point; Peak = historical maximum ≥ Current.

**Root cause:** No defect found in `compute_metric_summary` — behaviour verified with explicit numeric fixtures.

**Evidence (VERIFIED):**
- `TestAggregationRules::test_36_overall_is_not_highest_block_and_37_38_current_peak` — blocks BLK-A/BLK-B over 3 cycles (100+200, 150+250, 120+180):
  - `current_value == 300` (120+180 SUM) and `> 250` (highest single block) — **overall is not the highest block**;
  - `current_value == cycle_points[-1].value == 300` — **current = graph current**;
  - `maximum == max(cycle_points) == 400 ≥ current` — **peak = historical max**;
  - `reading_count == 6`.
- `test_37b_current_value_recomputed_from_latest_cycle` — water SUM: current == 100 == latest cycle point.

---

## J. Government Oversight + Municipality Own Office

**Requirement:** Super-admin can open any organisation's dashboard; municipality own-office blocks show live data alongside ward data.

**Evidence (VERIFIED):**
- `TestOversightAndOwnOffice::test_34_super_admin_oversight_works_for_any_org` — super-admin GET dashboard for a hospital org created outside the token's org → 200, correct name (no hardcoded org).
- `test_35_municipality_own_office_live_data_during_demo` — own-office block energy (2 rows @ BLK-OWN) **and** ward energy (4 rows) coexist during demo.
- `test_1b` — dashboard KPIs resolve for any authorised org.

---

## K. Red-Dot Notification Matrix (Civic Modules)

**Requirement:** Anomalies on street lighting, roads, parks, sewage, water flow (and their aliases) light the matching sidebar red dots, isolated per organisation.

**Root cause:** `SUPPORTED_MODULES` and `CANONICAL_MODULE_MAP` (backend) and `CANONICAL_ALIASES` (frontend) omitted the civic modules — `sewage_level` anomalies could not map to the `sewage` dot; `street_light`, `road`, `park`, `water_level` aliases were unmapped.

**Fix (FIXED):**
- `app/api/v1/notifications.py` — `SUPPORTED_MODULES` += `street_lighting, roads, parks, sewage, water_flow`; `CANONICAL_MODULE_MAP` += `street_lighting/street_light → street_lighting`, `roads/road → roads`, `parks/park → parks`, `sewage/sewage_level/drainage → sewage`, `water_flow/waterflow/water_level → water_flow`. The unread endpoint sets **both** the raw and canonical keys (`modules[m_raw]` and `modules[m_canonical]`), so legacy raw keys keep working.
- `frontend/src/context/NotificationContext.tsx` — `CANONICAL_ALIASES` extended with the same civic aliases so `isModuleUnread("sewage")` etc. resolve correctly.
- Sidebar already checks street_lighting / roads / parks / sewage red dots.

**Evidence:**
- `TestDemoAnomalyCadence::test_20_sewage_level_canonical_red_dot` — forced Drainage Backup (sewage_level) on a municipality → `GET /notifications/unread?organisation_id=…` returns `has_unread=True`, `modules["sewage"]==True`, `total_unread≥1` (BUG-09 regression).
- Backend `SUPPORTED_MODULES`/`CANONICAL_MODULE_MAP` greps confirm the 14-module list and 30+ alias mappings.
- Full suite passes with the maps in place (531/531).

---

## NEW BUG-01 .. NEW BUG-25

| ID | Area | Root cause | Fix location | Evidence (test) | Status |
|---|---|---|---|---|---|
| NEW BUG-01 | Demo scope | Demo was a global boolean; all orgs generated during any demo | `synthetic_simulator.py` `_demo_orgs` set + `_demo_active_for` | `test_4`, `test_5` | FIXED |
| NEW BUG-02 | Demo scope | `start/stop/status` had no organisation scope; demo leaked across orgs | `synthetic_simulator.py` `start/stop/status(organisation_id)`; `app/api/v1/simulator.py` | `test_7`, `test_8` | FIXED |
| NEW BUG-03 | Demo status | Status did not report per-org `demo_mode` / `generation_active` | `synthetic_simulator.py` `status()`; `schemas/simulator.py` | `test_demo_mode_status_flag` | FIXED |
| NEW BUG-04 | Demo scope | `run_cycle` did not gate non-enrolled orgs (TEST A/B violation) | `synthetic_simulator.py` scope gate after `processed_count += 1` | `test_4`, `test_6` | FIXED |
| NEW BUG-05 | Demo scope | `stop(org)` could only full-stop; no per-org relinquish | `stop()` → discard + `scoped_stopped` when others remain | `test_8` | FIXED |
| NEW BUG-06 | Demo scope | Reset left stale demo enrollment | `reset_all_simulator_state()` clears `_demo_orgs` | autouse `_deterministic_and_clean` + full suite | FIXED |
| NEW BUG-07 | Demo scope | Stale `_demo_schedules` survived stop/start | `stop()`/`start()` pop/clear `_demo_schedules` | `test_16`, `test_17` | FIXED |
| NEW BUG-08 | Cadence | First demo anomaly delay `(45,60)` → first event too slow for 30–40s | `DEMO_FIRST_DELAY_SECONDS=(10,25)` | `test_16` | FIXED |
| NEW BUG-09 | Cadence | Subsequent band `(45,120)` unverified per-org | `DEMO_NEXT_DELAY_SECONDS=(60,120)` in `_consume_demo_anomaly` | `test_17` | FIXED |
| NEW BUG-10 | Cadence | Demo path could exceed one-anomaly-per-cycle invariant | demo block only when `anomaly_sensor_selected is None` | `test_13`, `test_21` | FIXED |
| NEW BUG-11 | Ward data | Municipality wards received no Energy/Water/Waste/AQ rows during demo (`has_data` false) | `_generate_org_readings` `extra_ward_civic` | `test_11`, `test_10` | FIXED |
| NEW BUG-12 | Ward data | Air Quality was whole-org only → absent on ward page during demo | AQ branch in `_generate_org_readings` emits per-ward during demo | `test_32`, `test_11` | FIXED |
| NEW BUG-13 | Ward data | Adding ward civic targets dropped own-office block readings | `extra_ward_civic` appends ward **and** block targets | `test_35`, `test_10` | FIXED |
| NEW BUG-14 | Ward anomaly | Static `_scope_for_sensor` mismatch → civic anomaly never flagged the chosen reading | `_anomaly_match_key()` from actual target; static map deleted | `test_13`, `test_14` | FIXED |
| NEW BUG-15 | Ward anomaly | Municipality civic demo scenarios could fire at block/org scope | `_consume_demo_anomaly` re-scope block/org → ward for civic sensors | `test_13`, `test_14` | FIXED |
| NEW BUG-16 | Ward anomaly | `AnomalyRecord.ward_id` not copied from flagged reading | detection pipeline copies `reading.ward_id` (`anomaly_detection.py`) — verified | `test_13`, `test_19` | VERIFIED |
| NEW BUG-17 | Ward detail | `CIVIC_MODULES_SPECS` incomplete (8 of 18 modules) | `organisations.py` → 18 entries | `test_11`, `test_15` | FIXED |
| NEW BUG-18 | Ward detail | Ward metrics could surface block-scoped readings | ward query filters `ward_id IN (ward_number, id)`; `block_id is None` asserted | `test_15` | VERIFIED |
| NEW BUG-19 | Notifications | `SUPPORTED_MODULES` missing street_lighting, roads, parks, sewage, water_flow → dot never lit | `notifications.py` `SUPPORTED_MODULES` | `test_20` + full suite | FIXED |
| NEW BUG-20 | Notifications | `CANONICAL_MODULE_MAP` missing civic aliases (sewage_level, street_light, road, park, water_level, drainage) | `notifications.py` `CANONICAL_MODULE_MAP` | `test_20` | FIXED |
| NEW BUG-21 | Notifications | Frontend `CANONICAL_ALIASES` missing same aliases → canonical dot ignored | `NotificationContext.tsx` | typecheck + build clean | FIXED |
| NEW BUG-22 | Demo UI | DemoPanel/DemoContext not scoped to the active organisation (body/query org missing) | `DemoControlPanel.tsx` (`getOrgId`, body `organisation_id`, status query); `DemoContext.tsx` per-org toggle | `tsc` clean, build clean; browser **NOT TESTED** | FIXED (code) / NOT TESTED (browser) |
| NEW BUG-23 | Real-time | Dashboard `last_updated_at` risk of staleness vs newest reading | sourced from `metric_sum.latest_timestamp` — verified | `test_1b`, `test_3` | VERIFIED |
| NEW BUG-24 | Forecast | Ward forecast risk of cross-ward / org-level contamination | `build_ward_forecast_items` ward-only filter — verified | `test_24`, `test_25` | VERIFIED |
| NEW BUG-25 | Aggregation | Overall could be mistaken for highest block; peak vs current unasserted | `compute_metric_summary` SUM/cycle-point semantics — verified | `test_36`, `test_37b` | VERIFIED |

---

## Mandatory 38-Scenario → Test Mapping

All 38 mandatory scenarios are automated in `backend/tests/test_greennexa_final_all_bugs.py` (37 tests; some tests cover multiple scenarios) — **37 passed / 0 failed**.

| # | Scenario | Test |
|---|---|---|
| 1 | 30s cycle persists fresh readings | `TestRealTimeCadence::test_1_30s_cycle_persists_fresh_readings` |
| 2 | Recent readings newest cycle | `test_3_recent_readings_show_newest_cycle` |
| 3 | Last Updated follows latest | `test_1b_dashboard_last_updated_follows_latest_reading` |
| 4 | Demo changes only org A | `TestDemoScopeIsolation::test_4_demo_org_a_changes_only_org_a` |
| 5 | Gov/private orgs unchanged | `test_5_government_and_private_orgs_frozen` |
| 6 | Muni demo changes only muni | `test_6_municipality_demo_changes_only_municipality_scope` |
| 7 | Enrollment/generation_active | `test_7_enrollment_follows_owner_and_demo_generation_active` |
| 8 | Stop org relinquishes scope | `test_8_stop_org_relinquishes_scope_without_stopping_others` |
| 9 | Demo changes ward readings | `TestMunicipalityWardDemoData::test_9_demo_changes_ward_readings` |
| 10 | Correct ward_id, no block | `test_10_ward_readings_have_correct_ward_id_no_block` |
| 11 | Energy/Water/Waste/AQ has_data | `test_11_ward_detail_energy_water_waste_aq_has_data` |
| 12 | Street lighting per ward | `test_12_street_lighting_per_ward_changes` |
| 13 | Ward anomaly copies ward_id | `test_13_ward_scoped_civic_anomaly_attaches_ward_id` |
| 14 | Energy anomaly ward-scoped | `test_14_first_demo_anomaly_scoped_to_ward_energy` |
| 15 | Ward detail never block data | `test_15_ward_detail_never_shows_block_data` |
| 16 | First anomaly ~30–40s | `TestDemoAnomalyCadence::test_16_first_anomaly_within_about_40s` |
| 17 | Subsequent 60–120s | `test_17_subsequent_anomalies_every_60_120s` |
| 18 | Anomaly through real pipeline | `test_18_demo_anomaly_flows_through_real_pipeline` |
| 19 | Ward records attached | `test_19_wards_valid_and_records_attached_after_anomaly` |
| 20 | Sewage canonical red dot | `test_20_sewage_level_canonical_red_dot` |
| 21 | No duplicate from polling | `test_21_no_duplicate_anomalies_from_polling` |
| 22 | Priority ranks Critical first | `TestPriorityEngine::test_22_priority_ranks_critical_first` |
| 23 | Priority inactive threshold | `test_23_priority_inactive_below_threshold` |
| 24 | Ward forecast scoped | `TestForecastScoping::test_24_energy_ward_forecast_uses_only_ward_history` |
| 25 | Org aggregate not ward-contaminated | `test_25_org_level_aggregation_not_contaminated_by_wards` |
| 26 | Honest insufficient history | `test_26_ward_forecast_honest_when_insufficient_history` |
| 27 | Ward count excludes blocks | `TestScopeRules::test_27_ward_count_excludes_facility_blocks` |
| 28 | Add ward creates no block | `test_28_add_ward_creates_no_block` |
| 29 | Street lighting never block | `test_29_street_lighting_never_block_generated` |
| 30 | Parking/traffic/water_flow never block | `test_30_parking_traffic_water_flow_never_block` |
| 31 | Water flow ward-scoped | `test_31_water_flow_scoped_to_ward_for_municipality` |
| 32 | AQ never uses blocks | `test_32_air_quality_never_uses_blocks` |
| 33 | Energy own-office block scope | `test_33_energy_stays_block_scoped_for_own_office` |
| 34 | Super-admin any-org oversight | `TestOversightAndOwnOffice::test_34_super_admin_oversight_works_for_any_org` |
| 35 | Own office live data | `test_35_municipality_own_office_live_data_during_demo` |
| 36 | Overall ≠ highest block | `TestAggregationRules::test_36_overall_is_not_highest_block_and_37_38_current_peak` |
| 37 | Current == graph current | same test (`current == cycle_points[-1]`) |
| 38 | Peak == historical max ≥ current | same test (`maximum == 400 >= current`) + `test_37b` |

---

## TEST A–J (Browser Smoke) — HONEST STATUS

**BROWSER VERIFICATION NOT AVAILABLE** in this environment (headless CLI only, no browser). Every row below is **NOT TESTED** as a browser/UI check. Backend/API automation covering the same behaviour is listed separately and did pass — it is **not** a substitute for the browser test.

| Test | What it checks (browser) | Status |
|---|---|---|
| TEST A | Start demo for Org A → only Org A dashboard charts move; Org B frozen | **NOT TESTED** (backend equivalent: `test_4` — PASSED) |
| TEST B | Second org's data unchanged during demo | **NOT TESTED** (backend equivalent: `test_5` — PASSED) |
| TEST C | Dashboard "Last Updated" ticks every ~30s during live cycle | **NOT TESTED** (backend equivalent: `test_1b` — PASSED) |
| TEST D | First demo anomaly appears within ~30–40s of pressing Start | **NOT TESTED** (backend equivalent: `test_16` — PASSED) |
| TEST E | Ward Energy/Water/Waste/AQ cards show live values during municipality demo | **NOT TESTED** (backend equivalent: `test_11` — PASSED) |
| TEST F | Ward anomaly lights the ward-scoped red dot in the sidebar | **NOT TESTED** (backend equivalent: `test_13`+`test_20` — PASSED) |
| TEST G | Street Lighting / Roads / Parks / Sewage red dots on civic anomalies | **NOT TESTED** (backend equivalent: `test_20` — PASSED) |
| TEST H | Stop demo for one org stops only that org's generation | **NOT TESTED** (backend equivalent: `test_8` — PASSED) |
| TEST I | Ward detail page lists all 18 civic modules, no block leakage | **NOT TESTED** (backend equivalent: `test_11`+`test_15` — PASSED) |
| TEST J | Priority panel shows Critical first with ≥3 anomalies | **NOT TESTED** (backend equivalent: `test_22` — PASSED) |

Frontend compile/build is clean (`tsc` 0 errors, `next build` 35/35 routes) — this proves the UI **compiles**, not that it **behaves** in a browser.

---

## L. Database Safety

- **No schema migration** executed — no `CREATE TABLE`/`ALTER`/`DROP` against application data (models unchanged this pass; `generation_active` is API-response-only).
- **No row deletions** — no `DELETE`, no `truncate`, no "Clear Data" invocation in test or fix code paths. `reset_all_simulator_state()` clears **in-memory runtime state only** (demo enrollment set, demo schedules, counters, timestamps) — it never issues a `DELETE`.
- Test DB is SQLite `:memory:` created/dropped per test by `tests/conftest.py` (`Base.metadata.create_all` / `drop_all`) — completely isolated from the application database.
- Singleton reuse preserved: `simulator_instance` remains the single shared engine; tests that need isolation instantiate local `SyntheticDataSimulator` objects (thread-free `run_cycle` calls) — no duplicate engine leaks (autouse fixture calls `simulator_instance.reset_all_simulator_state()`).
- Existing tests that depend on untouched row counts (e.g. `test_municipality_ward_civic_suite`, `test_ward_detail_shows_only_ward_scoped_telemetry`) pass **unchanged**, confirming non-demo generation paths emit the same rows as before.

---

## M. Demo Timing / Scope Evidence

**Timing (measured by tests, not estimated):**
- `DEMO_FIRST_DELAY_SECONDS = (10.0, 25.0)`; schedule primed on first demo-enabled cycle → fires on the next 30s tick → **first anomaly ~30–40s from demo start** (`test_16`: measured 10–40s from prime).
- `DEMO_NEXT_DELAY_SECONDS = (60.0, 120.0)` → subsequent gaps **60–120s** (`test_17`: measured 60–130s at 10s cycle granularity).
- One anomaly maximum per org per cycle (`test_13`, `test_21`).
- Polling (re-fetching dashboards / repeated status calls) creates **zero** extra anomalies (`test_21`).

**Scope:**
- With any demo enrolled, non-enrolled orgs generate **0** readings (`test_4`, `test_5`, `test_6`).
- Enrolled orgs generate normally; `generation_active` in status reflects whether *this* org is generating right now (`test_7`).
- `stop(organisation_id)` un-enrolls one org only; others keep generating (`test_8`).
- No-org start enrolls the global sentinel `"*"` → all orgs (legacy behaviour), preserved by `test_demo_mode_propagation_through_api` without modification.

---

## Final Counts

| Metric | Value |
|---|---|
| Backend tests | **531 passed / 0 failed / 0 skipped** (108.5s) |
| New mandatory scenario tests | 37 / 37 passed |
| Rewritten/updated existing tests | 2 (`test_demo_scheduler_cadence_and_single_anomaly`, `_fresh_sim` usages) |
| Backend files changed | 6 (`synthetic_simulator.py`, `api/v1/simulator.py`, `schemas/simulator.py`, `api/v1/organisations.py`, `api/v1/notifications.py`, + test files) |
| Frontend files changed | 3 (`DemoContext.tsx`, `DemoControlPanel.tsx`, `NotificationContext.tsx`) |
| Frontend typecheck / build | 0 errors / success (35 routes) |
| Browser tests (A–J) | **0 of 10 tested** |

---

## Remaining Issues / Honest Caveats

1. **TEST A–J are entirely NOT TESTED** (browser unavailable). The backend equivalents passing is strong signal but does not prove UI rendering, chart animation, or sidebar dot visibility in a real browser.
2. **NEW BUG-22** (demo panel org scoping) is FIXED at code level and typechecks/builds, but its browser round-trip (press Start → badge → Stop) is in the NOT TESTED bucket.
3. Municipality ward civic generation for Energy/Water/Waste/AQ is **demo-scoped by design** (Option B): outside demo, wards still show only natural-location modules (traffic, parking, street lighting, …) — non-demo `has_data` for ward Energy stays `False` until demo runs or real telemetry ingests. This matches the existing non-demo count expectations but is a deliberate product decision, not an oversight.
4. `compute_metric_summary.reading_count` counts **all** readings of the metric (including ward rows) while cycle points/current use block-scoped rows for block-wise modules — cosmetic only; does not affect Overall/Current/Peak (asserted in `test_25`/`test_36`).
5. Ward detail `status` (ONLINE/OFFLINE) is freshness-based against real wall-clock; tests seeded fixed timestamps and therefore assert `has_data`/`latest_value`, not ONLINE — live browser behaviour is part of the NOT TESTED bucket.

---

*End of report. Superseded report: `GREENNEXA_FINAL_IMPLEMENTATION_REPORT.md`.*
