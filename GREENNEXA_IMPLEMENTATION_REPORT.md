# GREENNEXA IMPLEMENTATION REPORT
### Municipality / Ward / Own-Office / Oversight Fix Program (20 Fixes)
**Date:** 2026-09-24  
**Branch of work:** Fix 10 oversight + civic-module scoping + ward management + create-form setup modes + regression hardening  
**Platform:** GreenNexa Backend (FastAPI + SQLAlchemy) / Frontend (Next.js 16, React 19)

---

## 1. Executive Summary

All 20 fixes in this program were implemented at root-cause level (no placeholder code, no surface patches, no data destructive operations). The two critical behavioral outcomes are:

1. **Read-only municipality oversight (Fix 10):** A Municipality `ADMIN` can now view dashboard/anomaly/recommendation data of associated government organisations (association list stored in that org's `sensor_configs` JSON as `associated_gov_org_ids` / `_municipality_assoc`), while every write path (detect, update, delete) remains blocked by the strict `verify_organisation_access` gate.
2. **Civic module integrity (Fixes 6/7/8/9/16/19):** `street_lighting`, `roads`, `parks`, and `sewage` are first-class civic modules — present in the backend `ALLOWED_SENSOR_TYPES` + sensor catalog, present in the frontend `sensorCatalog.ts`, never `FacilityBlock`-scoped (they aggregate at organisation/ward level via `NATURAL_LOCATION_MODULES`), and surfaced in the sidebar + module page (street_lighting added to `isCumulative`).

**Final state: Backend 480 tests passed / 4 pre-existing-or-flaky failures (detail in §7). Frontend `tsc --noEmit` clean, `next build` green with new `/dashboard/wards/[ward_id]` route.**

---

## 2. Scope of the 20 Fixes — Implementation Map

| # | Fix area | Primary code touched |
|---|---|---|
| 1–5 | Ward ≠ FacilityBlock: separate `MunicipalityWard` entity; ward list never returns facility blocks; dashboard returns both blocks (own-office wings) and wards | `app/db/models.py`, `app/api/v1/organisations.py`, `app/api/v1/dashboard.py` |
| 6 | Backend sensor catalog adds civic modules | `app/core/sensor_catalog.py`, `app/db/models.py` (`ALLOWED_SENSOR_TYPES`) |
| 7 | Frontend sensor catalog adds civic modules | `frontend/src/lib/sensorCatalog.ts` |
| 8 | Ward detail page: honest `has_data:false` empty state, never fabricates data, never shows facility blocks | `app/api/v1/organisations.py` (`get_ward_detail`), `frontend/src/app/dashboard/wards/[ward_id]/page.tsx` |
| 9 | Civic readings scoped by `ward_id`, not by `block_id` | `app/core/aggregation.py`, ward queries |
| 10 | **Read-only municipality oversight access** | `app/core/dependencies.py` (`verify_oversight_read_access`), `app/api/v1/dashboard.py`, `anomalies.py`, `recommendations.py` |
| 11–12 | Municipality dashboard ward cards clickable → `/dashboard/wards/:id` | `frontend/src/components/municipality/MunicipalityDashboard.tsx` |
| 13 | create-full `municipality_setup_type`: `NORMAL_MUNICIPALITY` → wards, `OWN_OFFICE` → blocks | `app/api/v1/super_admin.py`, `app/schemas/super_admin.py` |
| 14 | Sidebar civic entries (Street Lighting, Roads & Infrastructure, Parks & Playgrounds, Drainage & Sewage) + `Energy (Own Office)` for municipality | `frontend/src/components/layout/Sidebar.tsx` |
| 15 | Module page cumulative handling for street_lighting | `frontend/src/app/dashboard/modules/[module_id]/page.tsx` |
| 16 | Aggregation: `current` = last cycle point, `peak` = MAX(cycle points) | `app/core/aggregation.py` |
| 17 | Aggregation: block-scoped readings with fallback to all readings (block-wise modules only) | `app/core/aggregation.py` |
| 18 | Database layer: latent NameErrors fixed; `sqlite:///` relative paths resolved CWD-independently | `app/db/database.py` |
| 19 | Civic/natural-location modules aggregated as mean, never block-deduped | `app/core/aggregation.py` (`NATURAL_LOCATION_MODULES`) |
| 20 | Own-office blocks (BLK-001..004) retained as wings; wards never convert to blocks | `app/db/models.py`, ward/block endpoints |

Also: super-admin municipality manage page switched to `/wards` load/create/delete endpoints; create form sends `municipality_setup_type` + `wards` (NORMAL) vs `blocks` (OWN_OFFICE); `sewage` added to `NATURAL_LOCATION_MODULES`.

---

## 3. Backend Changes (File-by-File)

- **`app/core/dependencies.py`** — Added `verify_oversight_read_access(requested_org_id, current_user, db)`: SUPER_ADMIN → any org; ADMIN → own org always; Municipality ADMIN → associated GOV orgs read-only (association read via `json.loads(cfg.sensor_configs)` — **must NOT use `sensor_configs_dict`** because that property merges defaults and silently drops non-dict list keys like the association lists). Returns 403 with explicit detail otherwise. `import json` present at module top. `verify_organisation_access` intact (verified: `app import OK; routes: 22`).
- **`app/api/v1/dashboard.py`** — `_get_org_and_config` gained `allow_oversight: bool = True` (all dashboard endpoints are reads). Under oversight with no stored config → builds an in-memory `OrganisationSensorConfig` **without persisting** (read-only semantics; auto-create persistence only for the org's own admin).
- **`app/api/v1/anomalies.py`**, **`app/api/v1/recommendations.py`** — list endpoints and org-or-single GET endpoints now call `verify_oversight_read_access`; all write endpoints (detect POST, PATCH, DELETE) still gated by `verify_organisation_access` / `require_roles`.
- **`app/core/aggregation.py`** — `NATURAL_LOCATION_MODULES` includes `street_lighting` (and civic `roads`/`parks`/`sewage`); these never fall into `FacilityBlock`-scoped branch.
- **`app/core/sensor_catalog.py`** — civic entries in `MASTER_SENSOR_CATALOG` + `RECOMMENDED_SENSORS_BY_TYPE["municipality"]`.
- **`app/db/models.py`** — `OrganisationSensorConfig.ALLOWED_SENSOR_TYPES` includes civic modules; `MunicipalityWard` entity distinct from `FacilityBlock`.
- **`app/api/v1/super_admin.py`** — `create-full` handles `municipality_setup_type` (`OWN_OFFICE` → blocks, `NORMAL_MUNICIPALITY` → `payload.wards` or fallback `payload.blocks` mapped to wards). Sensor config build retains established `recommended + enabled_modules` merge (see §7 — this behavior is load-bearing for `test_sensor_auto_selection`).
- **`tests/test_municipality_oversight_read.py`** — 5 tests (Fix 10).
- **`tests/test_municipality_ward_civic_suite.py`** — 15 tests (Fixes 2/3/5/6/7/8/9/13/16/19).
- **`tests/test_final_root_cause_fixes.py`** — 5 tests (Fixes 1/4/5 aggregation & scoping contract).
- **`app/db/database.py`** — Fix 18 (earlier phase): latent NameErrors resolved, CWD-independent DB path; verified on a DB copy, never touched live data destructively.

## 4. Frontend Changes (File-by-File)

- **`src/app/dashboard/wards/[ward_id]/page.tsx`** *(new)* — Ward detail page: `AppLayout` + `useAuth`; fetches `GET /api/v1/organisations/{orgId}/wards/{wardId}`; renders ward identity (number, name, zone), civic telemetry grid (latest value/unit/status badges, `—` + "No data collected yet." when `has_data:false`), ward-scoped anomaly list (severity/time), loading skeletons, 404/empty-state handling, and back-link to `/dashboard`.
- **`src/components/layout/Sidebar.tsx`** — Municipality sees `Energy (Own Office)` → `/dashboard/modules/energy`; conditional civic sub-items (street_lighting, roads, parks, sewage) gated by `isMunicipalityOrg` + `effectiveModules.includes(metric)`; `hasAnyModuleUnread` extended.
- **`src/app/super-admin/organisations/[org_id]/municipality/page.tsx`** — Wards tab uses `/wards` endpoints: list with `active_only=false`, create (`ward_name`), delete (soft-deactivate by ward id); renders `Ward {ward_number}` + name + INACTIVE badge.
- **`src/app/super-admin/create/page.tsx`** — `setupType` state (`NORMAL_MUNICIPALITY` | `OWN_OFFICE`); unit naming Wing/BLK vs Ward/WRD; municipality `enabled_modules` extended with civic modules; submit payload sends `municipality_setup_type` and `wards` (NORMAL) vs `blocks` (OWN_OFFICE/regular).
- **`src/types/index.ts`** — `FullOrganisationCreatePayload` extended with `wards?` and `municipality_setup_type?`.
- **`src/lib/sensorCatalog.ts`** — 4 civic sensor definitions + municipality recommended list extended.
- **`src/components/municipality/MunicipalityDashboard.tsx`** — ward cards are links to `/dashboard/wards/{id}`.
- **`src/app/dashboard/modules/[module_id]/page.tsx`** — `isCumulative` includes `"street_lighting"`.

---

## 5. Testing & Regression Results

**New regression tests added this effort (25 total, target was 22):**
- `tests/test_municipality_oversight_read.py` — **5 passed** (associated-gov 200 on dashboard/anomalies/recommendations + no config persisted + POST detect → 403; non-associated 403; regular admin 403; super admin 200; no civic sensor leakage).
- `tests/test_municipality_ward_civic_suite.py` — **15 passed** (ward create ⇒ no FacilityBlock; duplicate name 400; ward list never contains block fields; soft-delete; ward detail empty state / ward-scoped telemetry / cross-municipality 404 / ward-scoped anomalies; create-full NORMAL ⇒ wards & OWN_OFFICE ⇒ blocks; civic sensors in catalog + config; street_lighting not block-scoped with own-office blocks present; sewage/roads/parks module endpoints; dashboard civic current_values).
- `tests/test_final_root_cause_fixes.py` — **5 passed** (energy sum not highest block, temperature mean, current≤peak consistency, natural-location modules show no blocks, dashboard blocks+KPIs).

**Full backend suite:** `480 passed, 4 failed` (see §7).  
**Targeted create-full-affected suite after §6 experiment:** `51 passed, 1 failed (pre-existing)` — confirms no new regressions.  
**Frontend:** `npx tsc --noEmit` → clean. `npm run build` → green, route list includes `ƒ /dashboard/wards/[ward_id]`.

## 6. Database Integrity & Data-Safety

- Live DB (`backend/greennexa_test.db`, 5.8MB) **never deleted or reset**; all testing used in-memory SQLite (`DATABASE_URL=sqlite:///:memory:` override in `conftest.py`).
- Real-DB inspection scripts wrote only through non-destructive `UPDATE`/`ALTER` on `organisation_sensor_configs` (adding civic enabled sensors for `ORG-00002`), never row deletion.
- 0-byte shadow DB (`test/greennexa_test.db`) was never recreated.
- Fix 18 migration verified against a DB copy before any real-path use; `sqlite:///` relative URL now resolves against the backend directory, not process CWD.
- A temporary experiment editing `super_admin.py` `create-full` to honor explicit `enabled_modules` exactly was **reverted** (it broke the load-bearing `test_sensor_auto_selection` contract); the repo was restored to its prior (passing for that test) behavior — see §7.

## 7. Known Issues / Pre-existing Failures (NOT caused by this session)

1. **`test_clear_data_restart_regression::test_manual_organisation_creation_after_reset_persists_across_restart` — FAIL (pre-existing).** Root cause: a genuine spec conflict in the repo — this test asserts `enabled_sensors_list == ["energy","water","air_quality"]` exactly, while `test_sensor_auto_selection` (passing) *requires* `create-full` to auto-merge `RECOMMENDED_SENSORS_BY_TYPE[facility_type]` with `enabled_modules` (pump-station sensors must be present even when not explicitly listed). Both cannot hold simultaneously under a single merge rule. Verified: this test fails on the original, untouched `create-full` merge code (it failed at session start), so it is **not** a regression from this work. Resolution requires an owner decision on which contract to keep.
2. **`test_ai_assistant::test_short_query_metric_inference_from_context` — FAIL (pre-existing, LLM-text dependent).** Asserts literal `"Block C"` appears in the reply, but the live Gemini-generated Roman-Odia reply says `"Block RE"` (LLM free-form text). Not touched by any fix in this program.
3. **`test_ai_assistant::test_super_admin_total_organisation_kete_roman_odia` and `::test_super_admin_facility_type_counts` — FLAKY (order/LLM dependent).** Both **pass in isolation** (verified: `1 failed, 20 passed` when running `tests/test_ai_assistant.py` alone) and fail only during the full-suite run — reply wording (`"organisation"` vs `"organization"`, capitalization) varies with the generated text. Not a code regression.

**All other 480 tests pass.** No failures attributable to Fixes 1–20.

## 8. Verification Performed

| Check | Command / method | Result |
|---|---|---|
| Backend import sanity | `python -c "from app.main import app; print(len(app.routes))"` | `app import OK; routes: 22` |
| Oversight tests | `pytest tests/test_municipality_oversight_read.py -q` | 5 passed |
| Ward/civic tests | `pytest tests/test_municipality_ward_civic_suite.py -q` | 15 passed |
| Root-cause tests | `pytest tests/test_final_root_cause_fixes.py -q` | 5 passed |
| Full backend suite | `pytest tests -q` | **480 passed, 4 failed (pre-existing/flaky — §7)** |
| create-full affected files | `pytest tests/test_admin_sensor_config.py tests/test_sensor_auto_selection.py tests/test_task_spec_acceptance.py tests/test_clear_data_restart_regression.py ... -q` | 51 passed, 1 pre-existing fail |
| Frontend typecheck | `npx tsc --noEmit` | clean (0 errors) |
| Frontend production build | `npm run build` | green; `ƒ /dashboard/wards/[ward_id]` present |
| Association-key bug fix | unit test `test_oversight_uses_stored_associations_and_no_default_sensor_leak` | passed (raw JSON read, not `sensor_configs_dict`) |
| Edit-corruption recovery | full-suite `app import` after `dependencies.py` repair | OK |

## 9. Browser Verification Statement

**BROWSER VERIFICATION NOT AVAILABLE** — no browser automation tooling (Playwright/Puppeteer/CDP) was provisioned in this environment. Consequently, all frontend claims in this report are verified by: (a) static type checking (`tsc --noEmit` = 0 errors), (b) production compilation (`next build` success with the new dynamic route), and (c) code-level consistency review (all endpoints called by the new/changed pages match backend route signatures verified by tests). No claim of visual/pixel-level or click-path verification is made; manual UI walk-through in a browser remains recommended as a follow-up acceptance step.
