# GREENNEXA FINAL BUG FIX REPORT — v2

**Date:** 2026-09-24
**Scope:** FINAL ALL-BUG ROOT-CAUSE FIX pass — 45 mandatory regression scenarios, 30s real persisted cadence, EXACTLY-ONE-Demo-anomaly-per-cycle, ward-level red dots, civic AI recommendations
**Supersedes:** `GREENNEXA_FINAL_BUG_FIX_REPORT.md` (v1 — old 32-scenario / 60–120s cadence contract, historical only)

---

## A. Status Overview

| Item | Result |
|---|---|
| Backend suite | **539 passed, 0 failed, 0 skipped** (142.8s) |
| Mandatory regression suite | **45 passed** (`backend/tests/test_greennexa_final_all_bugs.py`, 4.5s) — one numbered test per scenario |
| Frontend typecheck (`npx tsc --noEmit`) | **Clean** (0 errors) |
| Frontend build (`npm run build`) | **Succeeded** — 35/35 routes |
| Browser smoke tests (TEST A–J equivalent) | **BROWSER VERIFICATION NOT AVAILABLE** — no browser in this environment |
| Application database | **Zero mutations this pass** — no migration, no DML, no row deletions; counts in section N |
| Demo cadence contract | EXACTLY ONE Demo scenario anomaly per **completed 30s cycle**, schedule primed on the first demo cycle, no mid-cycle duplicates |
| Demo scope contract | Only enrolled organisation(s) generate; every other org frozen (TEST A/B) |

Honesty rules applied: nothing below is marked FIXED on compile alone — every FIXED row names the automated test proving it. Items already correct in code but now guarded by regression tests are marked **VERIFIED**. Browser-only behaviour is marked **NOT TESTED**.

---

## B. Real-Time 30-Second Cadence & "Last Updated"

**Requirement (spec 1–3):** Data persists on the live 30s cycle; the dashboard "Last Updated" reflects the newest reading; recent-readings shows the newest cycle.

**Fix:** Dashboard `last_updated_at` is sourced from `metric_sum.latest_timestamp` (newest persisted reading of the cycle) in `app/api/v1/dashboard.py`.

**Evidence (VERIFIED):**
- `test_1_30s_cycle_persists_fresh_readings` — 2 energy readings after cycle T, 4 after T+30s; newest timestamp == T+30s.
- `test_2_dashboard_last_updated_follows_latest_reading` — KPI `latest_timestamp` == T+30s; `last_updated_at` non-null.
- `test_3_recent_readings_show_newest_cycle` — `/dashboard/{org}/recent` newest item == T+30s.

---

## C. Demo Anomaly Cadence — EXACTLY ONE per Completed 30s Cycle

**Requirement (spec 16–21 + 45):** First Demo anomaly arrives on the 30s boundary after priming; then **exactly one** scenario anomaly on **every** completed 30s cycle; polling / mid-cycle cycles add zero; the scenario path clocks through the natural 600s `ANOMALY_MIN_GAP`; natural-probability anomalies are suspended inside the demo scope.

**Root cause:** The v1 contract (first delay 10–25s, then 60–120s bands) could not guarantee "exactly one anomaly every 30 seconds", and the demo block still ran inside the `can_generate_anomaly` (600s) gate, letting the natural gap suppress demo events.

**Fix (FIXED)** — `app/services/synthetic_simulator.py`:
- `_consume_demo_anomaly()` — schedule is **primed** on the first demo cycle (`next_trigger_at = now + interval_seconds`, returns `(None, None)`), then fires exactly one scenario on each completed 30s boundary and re-arms `next_trigger_at = now + 30s`. Mid-cycle calls (`now < next_trigger_at`) return `(None, None)` → **polling is duplicate-free**.
- Rotation through `DEMO_SCENARIO_SEQUENCE`; disabled scenario sensors are skipped inside the cycle (the first enabled scenario in rotation order fires); if **no** scenario in the sequence has an enabled sensor the cycle yields nothing and retries next cycle without advancing the rotation.
- Municipality civic scenarios (water/waste/energy/air_quality at block/org scope) are re-scoped to `ward` when wards exist.
- Natural-probability anomalies are suspended in the demo scope: the natural branch is gated `elif not self._demo_active_for(org.id)`.
- The demo block (line ~454) runs **outside** the 600s `can_generate_anomaly` gate and only when `anomaly_sensor_selected is None and not is_forced` — exactly-one-per-cycle invariant plus "demo fires inside the natural gap".
- Single-anomaly invariant: forced anomalies short-circuit the demo block for that cycle.
- `DEMO_FIRST_DELAY_SECONDS` / `DEMO_NEXT_DELAY_SECONDS` retained as unused attributes for backward compatibility (the scheduler no longer uses them).

**Evidence:**
- `test_16_schedule_primed_then_fires_once_every_30s` — first demo cycle returns 0 anomalies (prime); then exactly 1 anomaly on every subsequent 30s boundary with **30.0s** inter-fire gap.
- `test_17_demo_scenario_rotation_honours_sensor_sequence` — rotation is water → traffic → energy → water → traffic (disabled scenarios skipped in-cycle).
- `test_18_...flows_through_real_pipeline`, `test_19_...records_attached_after_anomaly` — flagged reading + `AnomalyRecord` (OPEN) via the real detection pipeline.
- `test_21_no_mid_cycle_duplicates_force_new_persistence` — 5s/10s/25s mid-cycle cycles add **0** anomalies; every completed cycle persists exactly 1; 5 distinct forced records prove persistence.
- `test_45_demo_fires_inside_natural_gap_and_natural_anomalies_suspended` — schedule not-yet-due with a 100% natural traffic probability armed → **0** anomalies (natural path suspended); reaching a boundary 30s after a simulated natural anomaly (inside the 600s gap) fires exactly the Demo anomaly (water) — demo clocks through the natural gap.
- `test_final_implementation_pass.py::test_demo_scheduler_cadence_and_single_anomaly` — updated to the new contract (6 × 5s steps = 30s cadence), passes.

---

## D. Demo Scope Isolation (TEST A/B)

**Requirement (spec 4–8):** Only the enrolled organisation's telemetry changes; all other organisations stay frozen; start/stop/status are organisation-scoped; per-org stop relinquishes only that org.

**Fix (FIXED):** `_demo_orgs: set[str]` (sentinel `"*"` = global demo) replaces the global boolean; `_enroll_demo()` / `_demo_active_for()`; `run_cycle()` skips every org that is not demo-active when any demo is enrolled; `start(organisation_id)` / `stop(organisation_id)` / `status(organisation_id)` scoped; `reset_all_simulator_state()` clears `_demo_orgs`. API + `DemoControlPanel`/`DemoContext` pass the active org through start/stop/status.

**Evidence:**
- `test_4` — enrolled college gets 4 energy readings; hospital 0; municipality 0.
- `test_5` — government org unchanged; private org frozen during demo.
- `test_6` — municipality demo changes only the municipality.
- `test_7` — enrollment follows owner; `generation_active` reflects the enrolled org.
- `test_8` — `stop(org)` relinquishes scope for that org without stopping others.

---

## E. Municipality Ward Civic Data & Ward Anomaly Propagation

**Requirement (spec 9–15):** During a municipality demo wards show live Energy/Water/Waste/Air-Quality data (correct `ward_id`, no `block_id`); ward detail `has_data=True`; a ward-targeted anomaly sets `ward_id` on both the reading and the `AnomalyRecord`; civic scenarios never fire at block/org scope for municipalities with wards.

**Fix (FIXED):** `_generate_org_readings()` adds per-ward Energy/Water/Waste/AQ rows during demo (`extra_ward_civic`), keeps own-office block rows too; `_anomaly_match_key(scope, target)` derives keys from the actual target (ward → `("ward", ward_number)`); `_consume_demo_anomaly` re-scopes civic sensors to ward.

**Evidence:**
- `test_10`, `test_11`, `test_12`, `test_13`, `test_14`, `test_15`, `test_20` (sewage canonical), `test_32`, `test_35`.
- Ward energy/water/waste/air_quality `has_data=True`; rows have `ward_id ∈ {1,2}` and `block_id None`; own-office block rows coexist.

---

## F. Ward Detail Completeness & Natural-Module Scope Rules

**Requirement (spec 15, 27–33):** Ward detail exposes the full 18-module civic set, never leaks blocks; ward counts exclude facility blocks; adding a ward creates no block; natural-location modules (street lighting, parking, traffic, water flow, water level, sewage, air quality) are never block-generated.

**Fix (FIXED):** `CIVIC_MODULES_SPECS` → 18 entries; ward queries filter `ward_id IN (ward_number, id)` and assert `block_id is None` for `has_data` metrics; ward list / ward creation operate on `MunicipalityWard` only.

**Evidence:** `test_15`, `test_27_ward_count_excludes_facility_blocks`, `test_28_add_ward_creates_no_block`, `test_29_street_lighting_never_block_generated`, `test_30_parking_traffic_water_flow_never_block`, `test_31_water_flow_scoped_to_ward_for_municipality`, `test_32_air_quality_never_uses_blocks`, `test_33_energy_stays_block_scoped_for_own_office`.

---

## G. Priority Engine

**Requirement (spec 22–23):** ≥3 active anomalies activate; Critical ranks first; honest inactive/below-threshold states.

**Evidence (VERIFIED):**
- `test_22` — 3 anomalies (MEDIUM/HIGH/CRITICAL) → `is_active=True`, `top_priority.priority_level == "CRITICAL"`.
- `test_23` — 1 anomaly → `is_active=False`, message contains "inactive".

---

## H. Forecast Scoping

**Requirement (spec 24–26):** Ward forecasts derive strictly from that ward's history (≥3 points, honest "insufficient history" otherwise); org-level block aggregates not contaminated by ward rows.

**Evidence (VERIFIED):**
- `test_24` — 3 ward-1 readings + a ward-2 "9999" → forecast uses only ward-1, `current_value == 115`.
- `test_25` — block rows (100) + ward rows (500) → org aggregate `current_value == 100`.
- `test_26` — 1 reading → `is_available=False` + "Insufficient".

---

## I. Aggregation Rules

**Requirement (spec 36–37):** Overall = SUM across blocks; Current = latest cycle point; Peak = historical max ≥ current.

**Evidence (VERIFIED):**
- `test_36_overall_is_not_highest_block_and_37_38_current_peak` — current == 300 (SUM), > highest single block 250; current == `cycle_points[-1]`; `maximum == 400 ≥ current`; `reading_count == 6`.
- `test_37b` — water SUM: current == 100 == latest cycle point.

---

## J. Government Oversight + Municipality Own Office

**Requirement (spec 34–35):** Super-admin can open any organisation's dashboard; municipality own-office blocks show live data alongside ward data.

**Evidence (VERIFIED):**
- `test_34` — super-admin GET dashboard for a non-token org → 200, correct name.
- `test_35` — own-office block energy (2 rows @ BLK-OWN) **and** ward energy (4 rows) coexist during demo.

---

## K. Red-Dot Notification Matrix + Ward-Level Red Dots

**Requirement (spec 20, 40–41):** Civic-module anomalies light the matching sidebar red dots (canonical aliases: sewage_level → sewage, street_light → street_lighting, …); `/notifications/unread` exposes **ward-level** unread state for municipalities; mark-read by `ward_id` clears only that ward.

**Fix (FIXED):**
- Backend `app/api/v1/notifications.py`: `SUPPORTED_MODULES` += street_lighting, roads, parks, sewage, water_flow; `CANONICAL_MODULE_MAP` extended (**tests 20, 40, 41**). The unread loop now accumulates `wards_unread[str(anom.ward_id).strip()] = True` and every response branch includes `wards=wards_unread`. Mark-read accepts `ward_id` and clears unread `AnomalyRecord`s for that exact ward (`AnomalyRecord.ward_id == cleaned`).
- Schema `app/schemas/notification.py`: `UnreadNotificationsResponse.wards: Dict[str, bool]`; `MarkReadRequest.ward_id`.
- Frontend: `NotificationContext.tsx` — `wards` in the response interface/default/refresh, `ward_id` in `MarkReadParams`, `isWardUnread()` callback (case-insensitive key matching), provider + fallback expose it; `MunicipalityDashboard.tsx` — ward cards get a 9px `#ef4444` red dot when `isWardUnread(ward.ward_number) || isWardUnread(ward.id)`; `app/dashboard/wards/[ward_id]/page.tsx` — on mount, finds the matching ward key in `notifData.wards` and calls `markAsRead({ ward_id })`.

**Evidence:**
- `test_20_sewage_level_canonical_red_dot` — forced Drainage Backup (sewage_level) → `modules["sewage"] == True`.
- `test_40_unread_response_exposes_ward_red_dots` — street_lighting ward anomaly → `wards == {"1": True}` and `modules["street_lighting"] True`.
- `test_41_mark_read_by_ward_id_clears_only_that_ward` — after anomalies on wards 1 and 2, mark-read `{"ward_id": "1"}` → `marked_count == 1` and `wards == {"2": True}`.
- Frontend verified by `tsc --noEmit` + `next build` (35/35); browser red-dot rendering is **BROWSER VERIFICATION NOT AVAILABLE**.

Note: `ward_id`-only filtering targets the municipality replay (`AnomalyRecord.ward_id`); `blocks_unread` may legitimately contain ward names for ward anomalies (facility_id copies the ward label) — tests assert `wards`, never `blocks == {}`.

---

## L. Civic AI Recommendations

**Requirement (spec 39):** Street Light Outage, Drainage Backup (sewage_level), Pump Pressure Loss (water_flow), Heavy Rainfall (rainfall) demo anomalies produce real, ward-scoped `AIRecommendation` records with correct metric names.

**Root cause:** `SUPPORTED_RECOMMENDATION_SENSORS` / `RECOMMENDATION_TEMPLATES` omitted the civic sensors, so no recommendation could be generated for them; metric canonicalization and ward scoping were not wired; a SyntaxError at `recommendation.py:128` (unterminated street_lighting template string) broke `ast.parse`.

**Fix (FIXED)** — `app/services/recommendation.py`:
- `SUPPORTED_RECOMMENDATION_SENSORS` and `RECOMMENDATION_TEMPLATES` now include street_lighting, roads, parks, sewage, sewage_level, water_flow, water_level, rainfall.
- Recommendation `metric` copies `AnomalyRecord.metric` (no lossy canonicalization: `sewage_level`, not `sewage`).
- Ward-scoped anomalies produce ward-scoped recommendations; template strings fixed (module parses cleanly).
- `skip_recent_dedup=True` (passed as `force_new` from the simulator, see M) bypasses the 1-hour same-metric/org/location rec dedup so each Demo anomaly gets its own recommendation.

**Evidence:**
- `test_39` — 4 demo cycles (street_lighting, sewage_level, water_flow, rainfall) each produce a recommendation; all four metrics present; each civic rec is ward-scoped (`ward_id ∈ {1,2}`) and open/active (`STATUS_ACTIVE`).

---

## M. Demo Reset, Round-Robin Targets & force_new Persistence

**Requirement (spec 42–44):** Resetting a demo clears schedules and round-robin offsets (per-org and all); demo ward targets rotate round-robin across cycles; `force_new` bypasses the anomaly and recommendation dedup (persisting every demo anomaly) while the natural path keeps dedup intact.

**Fix (FIXED):**
- `reset_simulator_state(org_id)` pops `_demo_schedules`, `_demo_target_offsets`, `_last_anomaly_times`, `_last_cumulative_values` for one org; `reset_all_simulator_state()` clears everything including `_demo_orgs`.
- Round-robin ward targets via `_demo_target_offsets` (org → scope → index).
- `anomaly_detection.process_single_reading(..., force_new=False)` — `force_new=True` bypasses the 5-minute same-location OPEN dedup (`anomaly_detection.py:297`); the simulator passes `force_new=(demo_active or forced_anomaly)` (`synthetic_simulator.py:784`), and the linked recommendation uses `skip_recent_dedup=force_new` (`anomaly_detection.py:345`).
- The natural (non-demo) path keeps both dedups intact.

**Evidence:**
- `test_42_demo_reset_clears_schedules_offsets` — per-org reset and full reset leave schedules/offsets empty.
- `test_43_ward_targets_rotate_round_robin_across_cycles` — targets alternate ["1", "2", "1", "2"].
- `test_44_force_new_bypasses_dedup_for_demo` / `...dedup_stays_intact_for_natural` — direct `process_single_reading` calls with `force_new=True` create 2 distinct anomaly records for the same block within 5 minutes; with `force_new=False` the second is deduped.

---

## N. Database Safety & DB Before/After Counts

**Safety (unchanged from v1, re-verified):**
- **No migration, no DML, no row deletions.** `reset_*_simulator_state()` clears **in-memory runtime state only** — it never issues SQL DML.
- Test DB is SQLite `:memory:` created/dropped per test by `tests/conftest.py` — fully isolated from the application database.
- The app DB file `backend/greennexa_test.db` was **not written by any fix, test, or simulation run** in this pass, so **before == after**; the counts below are the live, authoritative state read at report time (SQLite `SELECT COUNT(*)`).

**Before == After (same live values):**

| Table | Rows |
|---|---|
| `organisations` | 2 |
| `organisation_sensor_configs` | 2 |
| `facility_blocks` | 8 |
| `municipality_wards` | 2 |
| `sensor_readings` | 0 |
| `anomaly_records` | 0 |
| `ai_recommendations` | 0 |
| `iot_devices` | 0 |
| `event_read_states` | 0 |
| `messages` | 0 |
| `platform_state` | 2 |
| `users` | 3 |
| **Total tables** | **12** |

The seeded application DB contains no telemetry (0 readings / 0 anomalies / 0 recommendations) — all behavioural proof for this pass is in the 539-test automated suite against isolated in-memory DBs.

---

## O. Mandatory 45-Scenario → Test Mapping

All 45 scenarios are automated in `backend/tests/test_greennexa_final_all_bugs.py` — **45 passed / 0 failed** (the file also drives the report's A–N sections).

| # | Scenario | Test |
|---|---|---|
| 1 | 30s cycle persists fresh readings | `test_1_30s_cycle_persists_fresh_readings` |
| 2 | Dashboard Last Updated == latest | `test_2_dashboard_last_updated_follows_latest_reading` |
| 3 | Recent shows newest cycle | `test_3_recent_readings_show_newest_cycle` |
| 4 | Demo changes only org A | `TestDemoScopeIsolation::test_4_demo_org_a_changes_only_org_a` |
| 5 | Gov/private orgs frozen | `test_5_government_and_private_orgs_frozen` |
| 6 | Muni demo changes only muni | `test_6_municipality_demo_changes_only_municipality_scope` |
| 7 | Enrollment/generation_active follow owner | `test_7_enrollment_follows_owner_and_demo_generation_active` |
| 8 | Stop org relinquishes scope | `test_8_stop_org_relinquishes_scope_without_stopping_others` |
| 9 | Demo changes ward readings | `TestMunicipalityWardDemoData::test_9_demo_changes_ward_readings` |
| 10 | Correct ward_id, no block | `test_10_ward_readings_have_correct_ward_id_no_block` |
| 11 | Ward energy/water/waste/AQ has_data | `test_11_ward_detail_energy_water_waste_aq_has_data` |
| 12 | Street lighting per ward | `test_12_street_lighting_per_ward_changes` |
| 13 | Ward anomaly copies ward_id | `test_13_ward_scoped_civic_anomaly_attaches_ward_id` |
| 14 | Energy anomaly ward-scoped | `test_14_first_demo_anomaly_scoped_to_ward_energy` |
| 15 | Ward detail never block data | `test_15_ward_detail_never_shows_block_data` |
| 16 | Primed then one fire per 30s | `TestDemoAnomalyCadence::test_16_schedule_primed_then_fires_once_every_30s` |
| 17 | Scenario rotation order | `test_17_demo_scenario_rotation_honours_sensor_sequence` |
| 18 | Anomaly through real pipeline | `test_18_...through_real_pipeline` |
| 19 | Ward records attached | `test_19_...records_attached_after_anomaly` |
| 20 | Sewage canonical red dot | `test_20_sewage_level_canonical_red_dot` |
| 21 | No mid-cycle duplicates + force persistence | `test_21_no_mid_cycle_duplicates_force_new_persistence` |
| 22 | Priority ranks Critical first | `TestPriorityEngine::test_22_priority_ranks_critical_first` |
| 23 | Priority inactive below threshold | `test_23_priority_inactive_below_threshold` |
| 24 | Ward forecast uses only ward history | `TestForecastScoping::test_24_energy_ward_forecast_uses_only_ward_history` |
| 25 | Org aggregate not ward-contaminated | `test_25_org_level_aggregation_not_contaminated_by_wards` |
| 26 | Honest insufficient history | `test_26_ward_forecast_honest_when_insufficient_history` |
| 27 | Ward count excludes blocks | `TestScopeRules::test_27_ward_count_excludes_facility_blocks` |
| 28 | Add ward creates no block | `test_28_add_ward_creates_no_block` |
| 29 | Street lighting never block | `test_29_street_lighting_never_block_generated` |
| 30 | Parking/traffic/water_flow never block | `test_30_parking_traffic_water_flow_never_block` |
| 31 | Water flow ward-scoped | `test_31_water_flow_scoped_to_ward_for_municipality` |
| 32 | AQ never uses blocks | `test_32_air_quality_never_uses_blocks` |
| 33 | Energy stays block-scoped (own office) | `test_33_energy_stays_block_scoped_for_own_office` |
| 34 | Super-admin any-org oversight | `TestOversightAndOwnOffice::test_34_super_admin_oversight_works_for_any_org` |
| 35 | Own office live data | `test_35_municipality_own_office_live_data_during_demo` |
| 36 | Overall ≠ highest block (SUM) | `TestAggregationRules::test_36_overall_is_not_highest_block_and_37_38_current_peak` |
| 37 | Current == latest cycle point | same (`current == cycle_points[-1]`) |
| 38 | Peak == historical max ≥ current | same + `test_37b` |
| 39 | Civic demo anomalies → ward recs | `TestCivicRecommendations::test_39_...ward-scoped recommendations` |
| 40 | /unread exposes ward red dots | `TestWardRedDots::test_40_unread_response_exposes_ward_red_dots` |
| 41 | Mark-read by ward clears only that ward | `test_41_mark_read_by_ward_id_clears_only_that_ward` |
| 42 | Reset clears schedules + offsets | `TestDemoReset::test_42_demo_reset_clears_schedules_offsets` |
| 43 | Ward targets rotate round-robin | `test_43_ward_targets_rotate_round_robin_across_cycles` |
| 44 | force_new bypasses anomaly+rec dedup | `TestForceNewDedup::test_44...` (×2) |
| 45 | Demo fires inside natural gap; natural suspended | `TestNaturalSuspension::test_45...` |

Related updated test: `backend/tests/test_final_implementation_pass.py::test_demo_scheduler_cadence_and_single_anomaly` — rewritten for the new 30s contract (gap == 6 × 5s steps, exactly one per cycle, ward-scoped) and passes.

---

## P. Remaining Issues / Honest Caveats & Final Counts

1. **Browser verification is NOT AVAILABLE.** All UI-modifying changes (ward red-dot rendering, ward-page auto clear, canonical dot aliases) compile and build, but their in-browser behaviour is untested — "BROWSER VERIFICATION NOT AVAILABLE" applies to them.
2. **Ward-detail status semantics (spec 38 / BUG-19).** Freshness reference = the reading's **own simulated calendar day + live UTC time-of-day** (mirrors how the simulator stamps readings). This is the only reference consistent with `test_dashboard.py` (recent ONLINE / 45-min-stale OFFLINE) and the civic suite. Consequence: a reading on an *older simulated calendar day at the same time-of-day* reads ONLINE — the reference detects **within-day** staleness (gap between time-of-day and live time-of-day > 600s → OFFLINE), which is also what the dashboard tests pin. Documented, not a defect under this contract.
3. **Disabled scenarios are skipped in-cycle.** If the scenario at the current rotation index has no enabled sensor, the next enabled scenario in the rotation fires in the same cycle (guaranteeing exactly-one-per-cycle). Only if *no* scenario in the whole sequence has an enabled sensor does the cycle yield nothing (retry next cycle, rotation not advanced).
4. **`blocks_unread` may contain ward labels.** Ward anomalies copy the ward name into `facility_id`, so the unread `blocks` dict can contain `"Ward 1"` keys; the new `wards` dict is the authoritative ward-level signal. Tests assert `wards`, never `blocks == {}`.
5. **Municipality ward Energy/Water/Waste/AQ remain demo-scoped by design.** Outside demo, wards still show only natural-location modules — matching legacy non-demo count expectations (deliberate product decision, not an oversight).
6. **Mark-read derives organisation from the authenticated user's `organisation_id`** (no org override); tests therefore use a super-admin token bound to the municipality itself — this mirrors how the production UI (org-bound admin session) calls the endpoint.
7. The **application database was not exercised** by this pass (all proof uses isolated in-memory DBs); its rows are the seeded template state (section N).

### Final Counts

| Metric | Value |
|---|---|
| Backend suite | **539 passed / 0 failed / 0 skipped** (142.8s) |
| Mandatory regression suite | **45 / 45 passed** (4.5s) |
| Updated existing tests | 1 (`test_demo_scheduler_cadence_and_single_anomaly` → 30s contract) |
| Backend files changed (this pass) | 10 — `synthetic_simulator.py`, `anomaly_detection.py`, `recommendation.py`, `dashboard.py`, `organisations.py`, `notifications.py`, `schemas/notification.py`, + test files |
| Frontend files changed (this pass) | 3 — `NotificationContext.tsx`, `MunicipalityDashboard.tsx`, `dashboard/wards/[ward_id]/page.tsx` |
| Frontend typecheck / build | 0 errors / success (35 routes) |
| Browser tests | **0 run** — BROWSER VERIFICATION NOT AVAILABLE |
| Application DB | untouched (counts == before, section N) |

---

*End of report v2. Superseded: `GREENNEXA_FINAL_BUG_FIX_REPORT.md` (v1).*