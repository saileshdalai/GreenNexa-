# GreenNexa — Master System Map & Technical Reverse-Engineering Specification

> **Document Status**: Production Complete & Verified from Implementation  
> **Source Base**: GreenNexa Multi-Tenant Sustainable Facility Intelligence Platform  
> **Verification Level**: 100% Code-Audited (APIs, Schemas, DB Models, Services, ML, Frontend Components, Contexts, and Test Suites)  
> **Security Protocol**: Strict Zero-Secret-Disclosure Applied (`[REDACTED]` for sensitive values)

---

## Table of Contents

1. [Architectural Overview & High-Level System Tree](#1-architectural-overview--high-level-system-tree)
2. [Project Structure Inventory](#2-project-structure-inventory)
3. [User & Role-Based Access Control (RBAC) System](#3-user--role-based-access-control-rbac-system)
4. [Authentication & Session Lifecycle](#4-authentication--session-lifecycle)
5. [Password Reset Mechanisms](#5-password-reset-mechanisms)
6. [Clear Data & Destructive Action Architecture](#6-clear-data--destructive-action-architecture)
7. [Super Admin Platform Interface Map](#7-super-admin-platform-interface-map)
8. [Normal Organisation Admin Interface Map](#8-normal-organisation-admin-interface-map)
9. [The Header ⋯ ("More") Menu — Complete Control Map](#9-the-header--more-menu--complete-control-map)
10. [Dashboard Presentation Style System](#10-dashboard-presentation-style-system)
11. [Theme & Colour Customization Engine](#11-theme--colour-customization-engine)
12. [Day & Night Mode Infrastructure](#12-day--night-mode-infrastructure)
13. [Autonomous Simulation Engine & Demo Mode](#13-autonomous-simulation-engine--demo-mode)
14. [Simulated Date & "Change Day" System](#14-simulated-date--change-day-system)
15. [Core & Civic Operational Modules](#15-core--civic-operational-modules)
16. [Facility Hierarchy & Spatial Scoping](#16-facility-hierarchy--spatial-scoping)
17. [Municipality Management & Cross-Facility Aggregation](#17-municipality-management--cross-facility-aggregation)
18. [Organisation Onboarding & Modification Lifecycle](#18-organisation-onboarding--modification-lifecycle)
19. [Master Sensor Catalog & Auto-Selection Engine](#19-master-sensor-catalog--auto-selection-engine)
20. [Database Schema & Entity Architecture](#20-database-schema--entity-architecture)
21. [End-to-End Data Flow Diagrams](#21-end-to-end-data-flow-diagrams)
22. [Hardware IoT Telemetry Ingestion System](#22-hardware-iot-telemetry-ingestion-system)
23. [AI & Machine Learning Engine](#23-ai--machine-learning-engine)
24. [Multilingual Conversational Assistant (Gemini)](#24-multilingual-conversational-assistant-gemini)
25. [What-If Predictive Scenario Simulator](#25-what-if-predictive-scenario-simulator)
26. [Anomaly Detection & Resolution Lifecycle](#26-anomaly-detection--resolution-lifecycle)
27. [Anomaly Priority Engine](#27-anomaly-priority-engine)
28. [Event Notification & "Red-Dot" Tracking Engine](#28-event-notification--red-dot-tracking-engine)
29. [Reporting & Audit Export Engine](#29-reporting--audit-export-engine)
30. [Database Storage Governance & Compaction](#30-database-storage-governance--compaction)
31. [Complete API Endpoint Map](#31-complete-api-endpoint-map)
32. [Frontend State Management Architecture](#32-frontend-state-management-architecture)
33. [Security Architecture & Multi-Tenant Isolation](#33-security-architecture--multi-tenant-isolation)
34. [Implemented vs Intended Feature Matrix](#34-implemented-vs-intended-feature-matrix)
35. [Known Constraints, System Risks & Architectural Boundaries](#35-known-constraints-system-risks--architectural-boundaries)
36. [Test Suite Inventory & Quality Assurance Report](#36-test-suite-inventory--quality-assurance-report)
37. [End-to-End Operational Lifecycle Story](#37-end-to-end-operational-lifecycle-story)
38. [Executive & Investor Presentation Summary](#38-executive--investor-presentation-summary)
39. [Code Traceability Index](#39-code-traceability-index)

---

## 1. Architectural Overview & High-Level System Tree

GreenNexa is a full-stack, multi-tenant sustainability and resource governance platform designed for universities, hospitals, industrial estates, schools, public facilities, and municipal city corporations. The system collects telemetry from physical IoT hardware (e.g. ESP32 / Arduino / Wokwi) or from an autonomous synthetic facility simulator, processes continuous data streams through a statistical and unsupervised ML pipeline, generates predictive forecasts, and surfaces actionable guidance via a localized, multilingual AI Assistant.

```
GreenNexa Root System
 ├── Frontend (Next.js 14 App Router, React 18, Vanilla CSS Design System)
 │    ├── Public Landing, About, Features, How-It-Works, Pricing, Contact
 │    ├── Unified Auth Interface (Government vs Private Scope Switcher, OTP Reset)
 │    ├── Super Admin Platform Portal (/super-admin)
 │    │    ├── Platform Overview, Org Matrix, User Management, Sensor Catalog
 │    │    ├── IoT Devices, Alerts, Reports, Platform Settings, Storage Governance
 │    ├── Tenant Admin Dashboard (/dashboard)
 │    │    ├── 4 Adaptable Styles (Executive, Operations, Analytics, Command Center)
 │    │    ├── 8 Core Facility Modules + 4 Civic Municipality Modules
 │    │    ├── AI Forecasting, Anomalies Lifecycle, Recommendations
 │    │    ├── Messages & Unread Notification Tracking ("Red Dot" engine)
 │    │    └── Municipality Civic Hub (Wards, Associated Gov Facilities)
 │    ├── Multilingual AI Assistant (Voice In/Out: English, Hinglish, Odia, Roman Odia)
 │    └── Global Presentation Contexts (Theme, Styles, Demo Mode, Notifications)
 │
 ├── Backend (FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy ORM)
 │    ├── API v1 Gateway (/api/v1)
 │    │    ├── auth, super-admin, organisations, dashboard, forecast
 │    │    ├── anomaly, recommendations, priority-engine, iot, messages
 │    │    ├── notifications, ai (assistant & scenario), reports, simulator
 │    ├── Core Engine
 │    │    ├── Security (PBKDF2 SHA-256, JWT Tokens, Destructive Confirmation)
 │    │    ├── Sensor Catalog (30+ sensor types, preselection, unit boundaries)
 │    │    └── Aggregation (Block-wise vs Natural civic location vs Whole-org)
 │    ├── Database Persistence Layer (SQLite / PostgreSQL / MySQL via SQLAlchemy)
 │    │    └── 13 Normalized Tables, Foreign Keys, Cascades, VACUUM Reclaim
 │    ├── Simulation Engine (SyntheticDataSimulator)
 │    │    ├── 30s Monotonic Interval, Per-Org & Per-Module Scoping
 │    │    ├── Cumulative Diurnal Metrics, Live Variable Metrics, Zero-Backlog
 │    │    └── Deterministic Demo Scenarios with Round-Robin Target Hopping
 │    ├── ML & Analytical Pipeline
 │    │    ├── Time-Series Forecasting (Statsmodels Holt-Winters Exponential Smoothing)
 │    │    ├── Tri-Layer Anomaly Detection (Threshold Rules, 3-Sigma Z-Score, IsolationForest)
 │    │    └── Priority Engine (Active Anomaly Thresholding & Dynamic Ranking)
 │    └── Conversational AI Integration
 │         ├── Gemini 2.5 Flash / Flash-Lite via Google GenAI SDK
 │         ├── Rule-Based Multi-Language NLU & Contextual Follow-up Extractor
 │         └── 15 Domain Tools (10 Tenant-Scoped, 5 Platform Super-Admin-Scoped)
 │
 └── IoT Telemetry Engine
      ├── Header Authentication (`X-Device-ID` + `X-API-Key`)
      ├── Source Isolation Mode Enforcement (`data_source == 'iot'`)
      └── Real-Time Synchronous Anomaly & AI Recommendation Pipeline
```

---

## 2. Project Structure Inventory

### Root & Configuration
- `package.json` — Root orchestration script declarations.
- `backend/` — Python FastAPI backend application.
- `frontend/` — Next.js 14 frontend web application.
- `greennexa_test.db` — Active primary local SQLite database file.

### Backend Structure (`backend/app/`)
- `main.py` — FastAPI application initialization, CORS configuration, router mounting, startup lifespan lifecycle (initializes database schemas and checks seed states).
- `api/v1/` — REST API route handlers:
  - `auth.py` — Authentication, login, JWT token issuance, self-service forgot-password OTP workflows.
  - `super_admin.py` — Platform overview, multi-step org creation, user management, administrative password reset, storage governance, Clear All Data.
  - `organisations.py` — Org profile, block management, ward management, government associations, sensor configuration, Admin Clear Data.
  - `dashboard.py` — Aggregated KPI metrics, module overviews, timeseries waveforms.
  - `forecast.py` — Multi-day Holt-Winters time-series forecast generation.
  - `anomaly.py` — Anomaly inspection, acknowledgment, resolution, and dismissal.
  - `recommendations.py` — AI recommendations listing and implementation status tracking.
  - `priority_engine.py` — High-priority anomaly evaluation (triggered at 3+ active events).
  - `iot.py` — Device registration, listing, and real sensor telemetry ingestion.
  - `messages.py` — Internal notifications and communication threads.
  - `notifications.py` — Granular unseen status tracking (modules, blocks, wards, sections).
  - `ai.py` — Conversational AI chat, suggestion starters, and What-If scenario execution.
  - `reports.py` — CSV and PDF export routes.
  - `simulator.py` — Synthetic simulator controls, date advancement, and demo mode switches.
- `core/` — Architectural utilities:
  - `config.py` — Central application settings via Pydantic BaseSettings (`.env` loading).
  - `security.py` — Password hashing, JWT token generation/validation, destructive confirmation validation.
  - `dependencies.py` — FastAPI dependencies (`get_current_user`, `require_roles`, `verify_organisation_access`).
  - `sensor_catalog.py` — Central repository of all supported sensor specifications, default thresholds, and automatic preselection maps.
  - `aggregation.py` — Module spatial categorization (`BLOCK_WISE_MODULES`, `NATURAL_LOCATION_MODULES`, `WHOLE_ORG_DEFAULT_MODULES`).
- `db/` — Database interface:
  - `database.py` — SQLAlchemy `engine`, `SessionLocal`, `get_db` generator, `safe_vacuum_sqlite`, file size readers.
  - `models.py` — 13 SQLAlchemy declarative ORM models.
  - `seed_demo.py` — Controlled startup database seeding with idempotent platform cleared verification.
- `schemas/` — Pydantic request and response transfer schemas.
- `services/` — Business logic implementations:
  - `synthetic_simulator.py` — Multi-threaded background synthetic data generation engine.
  - `anomaly_detection.py` — Tri-layer anomaly detection pipeline.
  - `anomaly_ml_service.py` — Scikit-Learn `IsolationForest` statistical model implementation.
  - `forecasting.py` — Statsmodels Holt-Winters Exponential Smoothing forecasting service.
  - `priority_engine.py` — Multi-factor severity/impact ranking engine.
  - `reporting.py` — CSV formatting and ReportLab PDF document compilation service.
  - `otp_service.py` — SMS-based OTP generator and validator.
  - `sms_service.py` — External SMS dispatch connector.
- `ai/assistant/` — Conversational AI subsystem:
  - `service.py` — Assistant controller, tenant isolation barrier, multi-turn state manager.
  - `nlu.py` — Regex and dictionary-based intent parser across 4 languages.
  - `gemini_tools.py` — Executable function declarations for Gemini function calling.

### Frontend Structure (`frontend/src/`)
- `app/` — Next.js App Router pages and layouts:
  - `page.tsx` — Public landing page.
  - `login/page.tsx` — Login interface with Government vs Private selector.
  - `forgot-password/page.tsx` — Self-service OTP phone password recovery.
  - `dashboard/page.tsx` — Main tenant dashboard (executes selected style composition).
  - `dashboard/modules/[module]/page.tsx` — Detailed sensor view per module.
  - `forecast/page.tsx` — Predictive trend charts and forecast horizon tables.
  - `anomalies/page.tsx` — Comprehensive anomaly monitoring and lifecycle management.
  - `recommendations/page.tsx` — Operational recommendations and impact estimates.
  - `messages/page.tsx` — Notifications center.
  - `reports/page.tsx` — Downloadable report builder (CSV / PDF).
  - `settings/page.tsx` — Tenant settings, sensor thresholds, Admin Clear Data modal.
  - `super-admin/` — Platform management sub-routes (`overview`, `create`, `organisations`, `users`, `sensors`, `iot`, `alerts`, `reports`, `settings`, `storage`).
- `components/` — UI building blocks:
  - `layout/` — `Header.tsx` (includes `⋯` dropdown), `Sidebar.tsx`, `AppLayout.tsx`, `Footer.tsx`.
  - `dashboard/` — Modular panels for KPIs, trends, alerts, style picker, color theme picker.
  - `ai/` — `GreenNexaAssistant.tsx` (floating launcher, speech input/output).
  - `municipality/` — `AddWardModal.tsx`, `AddGovernmentOrgModal.tsx`, `WardMetricsGrid.tsx`.
  - `super-admin/` — Admin creation wizards, storage breakdown tables, destructive modal dialogues.
- `context/` — Global state providers:
  - `AuthContext.tsx` — User session, JWT token, tenant switching, role permissions.
  - `DemoContext.tsx` — Autonomous simulation lifecycle, simulated date, 30s cycle timer.
  - `DashboardStyleContext.tsx` — Presentation layout engine (4 styles).
  - `ThemeContext.tsx` — Color palette (6 themes) and Day/Night mode controller.
  - `NotificationContext.tsx` — Unread count and red-dot indicator tracking.
  - `ToastContext.tsx` — Non-blocking notification toasts.
- `lib/` — Shared clients:
  - `api.ts` — HTTP client wrapper with automatic `Authorization: Bearer <token>` injection.
  - `dashboardStyles.ts` — Style registry, panel priorities, section requirements.
  - `organisation.ts` — Civic type detection helpers (`isMunicipality`).

---

## 3. User & Role-Based Access Control (RBAC) System

GreenNexa enforces strict Role-Based Access Control (RBAC) through the `User` model, verified at the backend via the FastAPI dependency `require_roles(...)` and mirrored at the frontend via route guards and conditional rendering.

### Identified Roles in Implementation
1. `SUPER_ADMIN` (`User.ROLE_SUPER_ADMIN = "SUPER_ADMIN"`) — Platform owner with global access.
2. `ADMIN` (`User.ROLE_ADMIN = "ADMIN"`) — Facility or Municipal administrator scoped to a single organization.

*(Note: While database models support foreign keys to users, no secondary operational roles such as `OPERATOR` or `VIEWER` are active in the current routing layer. All tenant accounts use role `ADMIN`.)*

### RBAC Permissions Matrix

| Platform Capability | SUPER_ADMIN | ADMIN | Verified Implementation Code |
| :--- | :---: | :---: | :--- |
| **Login to Platform** | Yes (Any Org Type) | Yes (Requires Org Type Match) | `backend/app/api/v1/auth.py:65-102` |
| **Switch Active Organization** | Yes (Global Dropdown) | No (Strictly Locked to Own Org) | `frontend/src/components/layout/Header.tsx:215-231` |
| **Access Platform Overview (`/super-admin`)** | Yes | No (HTTP 403 Forbidden) | `backend/app/core/dependencies.py:58-69` |
| **Create New Organisation & Admin** | Yes | No (HTTP 403 Forbidden) | `backend/app/api/v1/super_admin.py:228-470` |
| **Administrative Password Reset** | Yes (With Confirmation Pwd) | No | `backend/app/api/v1/super_admin.py:1154-1204` |
| **Self-Service Forgot Password** | Yes | Yes (Via Verified SMS OTP) | `backend/app/api/v1/auth.py:180-290` |
| **Full Platform Reset ("Clear All Data")** | Yes (Double Confirmation) | No (HTTP 403 Forbidden) | `backend/app/api/v1/super_admin.py:1868-1979` |
| **Organisation Reset ("Clear Data")** | Yes (For Any Org) | Yes (For Own Org Only) | `backend/app/api/v1/organisations.py:1306-1376` |
| **Manage Storage Governance** | Yes (`/super-admin/storage`) | No | `backend/app/api/v1/super_admin.py:1996-2128` |
| **View Operational Dashboard** | Yes (Selected Org) | Yes (Own Org) | `backend/app/api/v1/dashboard.py:40-120` |
| **Manage Facility Blocks** | Yes | Yes (Own Org) | `backend/app/api/v1/organisations.py:611-771` |
| **Manage Municipality Wards** | Yes | Yes (If Municipality Admin) | `backend/app/api/v1/organisations.py:802-950` |
| **Associate Gov Organisations** | Yes | Yes (If Municipality Admin) | `backend/app/api/v1/organisations.py:1453-1550` |
| **Configure Sensors & Baselines** | Yes | Yes (Own Org) | `backend/app/api/v1/organisations.py:513-581` |
| **Register & Manage IoT Devices** | Yes | Yes (Own Org) | `backend/app/api/v1/iot.py:213-270` |
| **Acknowledge / Resolve Anomalies** | Yes | Yes (Own Org) | `backend/app/api/v1/anomaly.py:110-180` |
| **Download CSV / PDF Reports** | Yes | Yes (Own Org) | `backend/app/api/v1/reports.py:98-150` |
| **Toggle Demo Mode** | Yes | Yes (Own Org) | `backend/app/api/v1/simulator.py:110-180` |
| **Advance Simulated Date ("Change Day")** | Yes | Yes (Own Org) | `backend/app/api/v1/simulator.py:40-105` |
| **Use Conversational AI Assistant** | Yes (Platform + Org Scope) | Yes (Strictly Scoped to Own Org) | `backend/app/ai/assistant/service.py:80-140` |

---

## 4. Authentication & Session Lifecycle

The authentication system employs JSON Web Tokens (JWT) signed with SHA-256 HMAC (`HS256`), salted password verification via PBKDF2 (`passlib.context.CryptContext(schemes=["pbkdf2_sha256"])`), and mandatory organisation ownership type validation for administrative users.

```
User Enters Email/ID, Password, & Org Type
                   │
                   ▼
       Frontend AuthContext.login()
                   │
                   ▼
        POST /api/v1/auth/login
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
Role: SUPER_ADMIN         Role: ADMIN
(Bypasses Org Check)           │
       │                       ▼
       │              Verify Organisation Status:
       │              - Is Organisation Active?
       │              - Does Ownership Type Match?
       │                (GOVERNMENT vs PRIVATE)
       │                       │
       └───────────┬───────────┘
                   ▼
        Verify User Status:
        - Does User Exist?
        - Is User is_active == True?
        - PBKDF2 Password Hash Match?
                   │
                   ▼
        Generate JWT Access Token
        (Payload: sub=user.id, role, org_id)
                   │
                   ▼
        Frontend Stores Token:
        - localStorage.setItem("greennexa_token", token)
        - Redirects to /dashboard or /super-admin
```

### Request Fields & Validation Logic
- **Endpoint**: `POST /api/v1/auth/login` (`backend/app/api/v1/auth.py:65`)
- **Payload**:
  - `email` (string, required): Accepts either the user's primary email address or user ID.
  - `password` (string, required): Plaintext password to be validated against the PBKDF2 hash.
  - `organisation_type` (string, optional for `SUPER_ADMIN`, mandatory for `ADMIN`): Accepts `"GOVERNMENT"` or `"PRIVATE"`.
- **Validation Rules**:
  1. *User Existence*: The user is resolved via case-insensitive email match or direct ID match (`backend/app/api/v1/auth.py:75-80`).
  2. *User Inactive*: If `user.is_active == False`, an `HTTP 403 Forbidden` ("User account is inactive.") is returned.
  3. *Password Verification*: Evaluated via `security.verify_password(password, user.hashed_password)`. On mismatch, returns `HTTP 401 Unauthorized` ("Incorrect email or password.").
  4. *Super Admin Exemption*: Users with `role == "SUPER_ADMIN"` bypass organisation checks and can access the entire platform.
  5. *Admin Ownership Validation*: If the user is an `ADMIN`:
     - Looks up `user.organisation`. If missing or `organisation.is_active == False`, returns `HTTP_403_FORBIDDEN` ("Organisation is inactive.").
     - Validates `user.organisation.ownership_type` against the provided `organisation_type`. If a Government Admin attempts to log in with "Private" selected (or vice versa), an `HTTP 401 Unauthorized` ("Invalid credentials or organisation type mismatch") is raised.
  6. *Token Creation*: Generates a signed JWT with expiration determined by `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 480 minutes / 8 hours). Payload: `{"sub": user.id, "role": user.role, "organisation_id": user.organisation_id, "exp": ...}`.
  7. *Logout Mechanics*: Calling `logout()` stops any active simulation for the organisation via `POST /api/v1/simulator/synthetic/stop`, calls `POST /api/v1/auth/logout`, purges all token items from `localStorage`, and redirects to `/`.

---

## 5. Password Reset Mechanisms

GreenNexa provides two distinct, fully implemented password reset pathways:

### A. Administrative Password Reset (Super Admin)
- **Component**: `frontend/src/app/super-admin/users/page.tsx`
- **Endpoint**: `POST /api/v1/super-admin/users/{user_id}/reset-password` (`backend/app/api/v1/super_admin.py:1154`)
- **Security Barrier**: Protected by the product owner's mandatory confirmation password (`GREENNEXA_DESTRUCTIVE_ACTION_PASSWORD`).
- **Execution Flow**:
  1. Super Admin opens the User Management table and clicks **Reset Password** on any user card.
  2. A secure modal prompts for:
     - *Confirmation Password* (Super Admin destructive secret).
     - *New Password* (minimum 6 characters).
     - *Confirm New Password* (must match exactly).
  3. Pre-flight check calls `POST /api/v1/super-admin/verify-confirmation-password`.
  4. The reset request transmits `new_password`, `confirm_new_password`, and `confirmation_password`.
  5. The backend validates the confirmation password, hashes `new_password` via PBKDF2 SHA-256, assigns it to `user.hashed_password`, and commits the transaction to the database.
  6. The password change is permanent and persists across application and database restarts.

### B. Self-Service Forgot Password (End-User SMS OTP)
- **Component**: `frontend/src/app/forgot-password/page.tsx`
- **Endpoints**:
  - `POST /api/v1/auth/forgot-password/request` (`backend/app/api/v1/auth.py:180`)
  - `POST /api/v1/auth/forgot-password/verify-otp` (`backend/app/api/v1/auth.py:220`)
  - `POST /api/v1/auth/forgot-password/reset-password` (`backend/app/api/v1/auth.py:255`)
- **Execution Flow**:
  1. *Initiation*: User enters their registered Indian phone number (10-digit format starting with 6-9, normalized with `+91`).
  2. *OTP Dispatch*: Backend generates a 6-digit numeric OTP, computes a cryptographic hash, stores it in `password_reset_otps` with a 10-minute expiry, and dispatches the code via `sms_service`.
  3. *OTP Verification*: User submits the OTP. Backend checks expiration, attempt counter, and validates the hash. On success, an ephemeral reset authorization token is returned.
  4. *Password Update*: User submits the new password accompanied by the reset token. Backend hashes the password, updates `User.hashed_password`, invalidates the OTP record, and commits.

---

## 6. Clear Data & Destructive Action Architecture

GreenNexa implements two clearly defined levels of data clearing to accommodate routine facility operational testing and full platform decommissioning.

```
                     CLEAR DATA CAPABILITIES
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
ADMIN ORGANISATION RESET                     SUPER ADMIN PLATFORM RESET
(Tenant Settings Page)                      (Platform Settings Page)
        │                                               │
Target: Single Organisation                     Target: Entire Database
Trigger: Active Org Admin / Super Admin         Trigger: Super Admin Only
Authorization: Standard User Token             Authorization: Mandatory Secret Password
                                                Confirmation: Exact string "CLEAR ALL DATA"
        │                                               │
Deletes:                                        Deletes:
- Sensor Readings (Org scoped)                  - ALL Sensor Readings (Every Org)
- Anomalies (Org scoped)                        - ALL Anomalies
- AI Recommendations (Org scoped)               - ALL AI Recommendations
- Messages (Org scoped)                         - ALL Internal Messages & Read States
- Event Read States (Org scoped)                - ALL IoT Devices
                                                - ALL Facility Blocks & Municipality Wards
Preserves:                                      - ALL Sensor Configs
- Organisation Entity Record                    - ALL Tenant Organisations
- Admin User Credentials                        - ALL Admin Users
- Facility Blocks & Wards                       
- Sensor Configurations & Baselines             Preserves:
- Registered IoT Device Identities              - Fixed Super Admin Account
                                                
        │                                               │
Post-Clear Compaction:                          Post-Clear Compaction:
- SQLite VACUUM Executed                        - Platform marked as destructively cleared
- Simulator Cache Reset                         - SQLite VACUUM Executed
- Forecasting Cache Cleared                     - Simulator Completely Stopped
```

### Deleted vs Preserved Comparison Table

| Data Entity | Admin Clear Data (`/organisations/{id}/clear-data`) | Super Admin Clear All Data (`/super-admin/clear-all-data`) |
| :--- | :---: | :---: |
| **Sensor Readings (`sensor_readings`)** | **DELETED** (Target Org Only) | **DELETED** (Entire Platform) |
| **Anomalies (`anomaly_records`)** | **DELETED** (Target Org Only) | **DELETED** (Entire Platform) |
| **AI Recommendations (`ai_recommendations`)**| **DELETED** (Target Org Only) | **DELETED** (Entire Platform) |
| **Notification Read States (`event_read_states`)**| **DELETED** (Target Org Only) | **DELETED** (Entire Platform) |
| **Internal Messages (`messages`)** | **DELETED** (Target Org Only) | **DELETED** (Entire Platform) |
| **IoT Hardware Devices (`iot_devices`)** | **PRESERVED** | **DELETED** |
| **Facility Blocks (`facility_blocks`)** | **PRESERVED** | **DELETED** |
| **Municipality Wards (`municipality_wards`)** | **PRESERVED** | **DELETED** |
| **Sensor Thresholds / Config (`organisation_sensor_configs`)** | **PRESERVED** | **DELETED** |
| **Tenant Organisation Profile (`organisations`)**| **PRESERVED** | **DELETED** |
| **Admin User Accounts (`users`)** | **PRESERVED** | **DELETED** (Except Super Admin) |
| **Fixed Super Admin User (`superadmin@...`)** | **PRESERVED** | **PRESERVED** |
| **SQLite Disk Reclamation (`VACUUM`)** | **EXECUTED** | **EXECUTED** |
| **Restart Reseeding Suppression** | N/A (Org Still Exists) | **ACTIVATED** (`set_platform_data_cleared`) |

*(Verified in `backend/app/api/v1/organisations.py:1306-1376` and `backend/app/api/v1/super_admin.py:1868-1979`)*

---

## 7. Super Admin Dashboard

The Super Admin interface (`/super-admin`) provides global oversight and multi-tenant management across all enrolled facilities and municipal bodies.

### Navigation Sidebar Controls (`frontend/src/components/layout/Sidebar.tsx:146-165`)
1. **Platform Overview** (`/super-admin`): Live high-level metrics including total organisations, total active users, active anomaly counts, total readings recorded, and an interactive organisation status table.
2. **Create** (Dropdown):
   - **Organisation** (`/super-admin/create?entity=organisation`): Launches the unified multi-step organisation and administrator creation wizard.
   - **Facility** (`/super-admin/create?entity=facility`): Pre-selects campus/facility configuration templates.
3. **Organisations** (`/super-admin/organisations`): Complete list of tenant organisations with status badges (Active/Inactive), ownership indicators (Government/Private), facility types, quick edit buttons, and soft deactivation/reactivation toggles.
4. **Users / Admins** (`/super-admin/users`): Platform-wide user catalog with details on role, affiliated organization, contact numbers, last login timestamps, user status toggle, and the confirmation-password-protected **Reset Password** trigger.
5. **Sensor Configuration** (`/super-admin/sensors`): Global sensor matrix displaying enabled metrics, baselines, warning thresholds, and critical thresholds across all organisations.
6. **IoT Devices** (`/super-admin/iot`): Registry of all registered hardware IoT devices, active status, associated organization, last heartbeat timestamp, and registration dialog.
7. **Organisation Monitoring** (`/super-admin/monitoring`): Real-time health metrics, active anomalies, and telemetry freshness across tenants.
8. **Platform Alerts** (`/super-admin/alerts`): Centralized operational alerts and high-severity platform events.
9. **Reports** (`/super-admin/reports`): Cross-organisation comparative reporting and telemetry audit exports.
10. **Platform Settings** (`/super-admin/settings`): Appearance toggles, facility type definitions, and the confirmation-password-protected **Clear All Data** modal.

### Super Admin Top Header Controls (`frontend/src/components/layout/Header.tsx:215-231`)
- **Organisation Switcher Dropdown**: Allows the Super Admin to select any active tenant organisation. Changing this selection updates `activeOrgId`, dynamically switching the entire dashboard context to reflect that specific facility's operational telemetry.
- **"Manage Storage"**: Accessible via the header `⋯` menu, linking directly to `/super-admin/storage`.

---

## 8. Normal Organisation Admin Dashboard

When an `ADMIN` logs in, they are directed to `/dashboard`, scoped strictly to their own organisation.

### Top Header Bar
- **Branding**: GreenNexa official logo.
- **Simulated Calendar Pill**: Displays the current operational date (e.g. `20 Sep 2026 / SUN`). Clicking opens a modal for manual date selection.
- **Simulation Cycle Indicator**: Displays an animated glowing green dot with a live seconds counter (`Cycle: Xs / 30s`) whenever Demo Mode is active.
- **Options Menu (⋯)**: Unified menu containing dashboard styles, color themes, municipal actions, and session controls.

### Sidebar Menu Structure (`frontend/src/components/layout/Sidebar.tsx:96-143`)
- **Overview** (`/dashboard`): Primary operational dashboard rendering the active Dashboard Style.
- **Modules** (`/dashboard/modules`): Expandable menu showing all enabled modules for the organisation. Dynamically shows a red alert dot if unseen anomalies exist in that module:
  - Energy
  - Water Supply
  - Waste Management
  - Air Quality
  - Traffic & Parking
  - Parking
  - Municipal Assets
  - Safety & Incidents
  - Climate & Environment
  - *(Civic modules if Municipality: Street Lighting, Roads, Parks, Drainage/Sewage)*
- **AI Forecast** (`/forecast`): Interactive time-series projection charts with multi-horizon selection (24 Hours, 7 Days, 15 Days, 30 Days).
- **Anomalies** (`/anomalies`): Real-time anomaly table with severity badges (Critical, High, Medium, Low), status indicators (Open, Acknowledged, Resolved, Dismissed), and action buttons. Displays an unread red dot with total event count.
- **Recommendations** (`/recommendations`): Prioritized list of prescriptive recommendations generated by the AI engine, showing potential energy/water savings and root causes.
- **Messages** (`/messages`): Internal message threads, system notifications, and audit alerts with an unread badge.
- **Reports** (`/reports`): Custom report generator for CSV and PDF downloads.
- **Settings** (`/settings`): Organisation sensor toggles, baseline/threshold modifiers, data source switch (Synthetic vs IoT), and the **Clear Data** operational reset modal.

---

## 9. The Header ⋯ ("More") Menu — Complete Control Map

The header `⋯` button (`#dashboard-more-menu-btn`) opens a centralized operational dropdown menu implemented in `frontend/src/components/layout/Header.tsx:281-560`.

```
⋯ (More Options Menu)
│
├── 1. Dashboard Style (Submenu) ────────── [Available to: ALL Users]
│      ├── Executive                     [Hero KPIs, High-Level Health First]
│      ├── Operations                    [Quick Actions, Live Alerts, Dense Cards]
│      ├── Analytics                     [Metric Charts, Trend Analysis, Tables]
│      └── Command Center                [Spatial Overview, Mission Control Map]
│
├── 2. Theme / Colour (Submenu) ─────────── [Available to: ALL Users]
│      ├── Emerald                       [Default Brand Green #10b981]
│      ├── Ocean Blue                    [Civic Water Blue #0284c7]
│      ├── Indigo                        [Executive Violet #6366f1]
│      ├── Teal                          [Coastal Teal #14b8a6]
│      ├── Graphite                      [Industrial Gray #64748b]
│      └── Amber                         [Energy Amber #f59e0b]
│
├── 3. Add (Submenu) ────────────────────── [CONDITION: Municipality Orgs ONLY]
│      ├── Ward                          [Opens AddWardModal dialog]
│      └── Organisation                  [Opens AddGovernmentOrgModal dialog]
│
├── 4. Manage Storage ───────────────────── [CONDITION: SUPER_ADMIN Role ONLY]
│                                        [Links to /super-admin/storage]
│
├── 5. Change Day ───────────────────────── [Advances simulation calendar +1 day]
├── 6. Demo Mode ON/OFF ─────────────────── [Toggles autonomous 30s cycle for active module]
├── 7. Notifications ────────────────────── [Navigates to /messages, shows red dot & count]
├── 8. ☀ Day Mode / 🌙 Night Mode ───────── [Toggles light surface vs dark obsidian themes]
├── 9. Logout ──────────────────────────── [Stops org simulator, purges tokens, redirects]
├── 10. Pricing ─────────────────────────── [Links to public /pricing]
├── 11. Contact Us ──────────────────────── [Links to public /contact]
└── 12. Privacy Policy ──────────────────── [Links to public /privacy]
```

### Detailed Item Action & Persistence Specifications

| Menu Item | Visibility Condition | Component / Route Triggered | Backend API Impact | Persistence Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **Dashboard Style** | All Logged-In Users | `DashboardStyleMenu.tsx` | None (Client Presentation) | `localStorage` (`greennexa_dashboard_style:<org_id>`) |
| **Theme / Colour** | All Logged-In Users | `ThemeColorMenu.tsx` | None (Client Presentation) | `localStorage` (`greennexa_color_theme`) + DOM attribute |
| **Add → Ward** | `isMunicipalityOrg == true` | `AddWardModal.tsx` | `POST /organisations/{id}/wards` | Database table `municipality_wards` |
| **Add → Organisation**| `isMunicipalityOrg == true` | `AddGovernmentOrgModal.tsx` | `POST /organisations/{id}/associated-government-orgs` | Database `organisation_sensor_configs.sensor_configs` JSON |
| **Manage Storage** | `user.role == 'SUPER_ADMIN'` | Router to `/super-admin/storage` | `GET /super-admin/storage` | Database inspection |
| **Change Day** | All Logged-In Users | `changeSimulatedDay(1)` | `POST /simulator/synthetic/change-day` | Database `simulated_date` + `localStorage` |
| **Demo Mode** | All Logged-In Users | `toggleDemoMode(module)` | `POST /simulator/synthetic/start` or `/stop` | In-memory simulator worker threads + `localStorage` |
| **Notifications** | All Logged-In Users | Router to `/messages` | `GET /messages/unread-count` | Database table `messages` / `event_read_states` |
| **Day / Night Mode**| All Logged-In Users | `toggleTheme()` | None (Client Presentation) | `localStorage` (`greennexa_theme`) + DOM attribute |
| **Logout** | All Logged-In Users | `handleLogout()` | `POST /auth/logout` + `POST /simulator/synthetic/stop` | Clears all `localStorage` auth and state keys |

---

## 10. Dashboard Style System

The Dashboard Style System (`frontend/src/lib/dashboardStyles.ts`) alters the layout priority, card density, and visualization emphasis of the dashboard without changing any underlying data.

### The 4 Presentation Styles

1. **Executive Style (`EXECUTIVE`)**
   - *Target Audience*: Executive leadership, board members, city mayors.
   - *Lead Element*: Full-width Overall Facility Health Summary card.
   - *Card Structure*: Large "Hero" KPI cards (minimum 300px width, max 4 cards rendered).
   - *Visual Emphasis*: Summaries first; critical alerts and AI-driven high-level insights take precedence; operational noise and dense tables are hidden or pushed to the bottom.

2. **Operations Style (`OPERATIONS`)**
   - *Target Audience*: Facility managers, mechanical engineers, control room operators.
   - *Lead Element*: Quick Actions and Live Priority Alert bar.
   - *Card Structure*: Compact, dense KPI cards (minimum 200px width, up to 8 cards rendered).
   - *Visual Emphasis*: Highlights active threshold breaches, active maintenance tasks, real-time sensor deviations, and urgent remediation actions.

3. **Analytics Style (`ANALYTICS`)**
   - *Target Audience*: Sustainability officers, data analysts, environmental compliance auditors.
   - *Lead Element*: Metric Comparison Trend Waveform and Historical Charts.
   - *Card Structure*: Full tabular layouts (minimum 180px, no card limit).
   - *Visual Emphasis*: Chart-heavy composition emphasizing historical standard deviations, 30-day multi-horizon trends, statistical variance, and export options.

4. **Command Center Style (`COMMAND_CENTER`)**
   - *Target Audience*: Municipal commissioners, large smart campus central dispatchers.
   - *Lead Element*: Spatial Ward Overview and Cross-Facility Map Status.
   - *Card Structure*: Radial progress gauges and status chips (minimum 170px, max 6 cards).
   - *Visual Emphasis*: Spatial visualization of physical wards, high-density incident distribution, civic alert queues, and cross-facility status indicators.

*(Technical Guarantee: `resolveSections()` in `dashboardStyles.ts:349` drops sections when underlying data does not exist, ensuring a selected style never invents artificial metrics).*

---

## 11. Theme & Colour Customization Engine

GreenNexa provides a dual-axis visual engine: an independent **Color Theme** axis and an independent **Day/Night Mode** axis, coordinated via `ThemeContext.tsx`.

### The 6 Color Themes
- **Emerald** (`#10b981`): Default brand theme. Represents organic sustainability, energy efficiency, and environmental balance.
- **Ocean Blue** (`#0284c7`): Professional civic theme. Tailored for municipal water utilities and institutional campuses.
- **Indigo** (`#6366f1`): Modern executive theme. Deep violet tones tailored for corporate enterprise campuses.
- **Teal** (`#14b8a6`): High-contrast clean theme. Optimised for clinical healthcare and laboratory environments.
- **Graphite** (`#64748b`): Minimalist industrial theme. Neutral slate palette designed for manufacturing and plant operations.
- **Amber** (`#f59e0b`): High-visibility warning theme. Warm amber accents highlighting energy optimization and physical asset maintenance.

### Implementation Mechanism
- Color themes set the DOM attribute `data-color-theme="<theme_name>"` on `document.documentElement` and `document.body`.
- Dynamically remaps CSS tokens: `--clr-primary`, `--clr-primary-hover`, `--clr-primary-light`, and `--clr-primary-glow`.
- Independent of Day/Night mode: All 6 color themes render with tailored contrast ratios in both Day (light) and Night (dark) surfaces.
- Dispatches a custom window event `greennexa_color_theme_changed` to trigger re-renders in Chart.js / SVG visualization canvases.

---

## 12. Day / Night Mode

- **Day Mode (`data-theme="day"`)**: Professional clean light aesthetic. Background: `#f8fafc`, Card Surface: `#ffffff`, Primary Text: `#0f172a`, Border: `#e2e8f0`.
- **Night Mode (`data-theme="night"`)**: Obsidian dark control room aesthetic. Background: `#090d16`, Card Surface: `#111827`, Primary Text: `#f9fafb`, Border: `#1f2937`.
- **State Storage**: Stored in `localStorage` under `greennexa_theme`.
- **Chart Synchronization**: Emits window event `greennexa_theme_changed` so chart axis labels, gridlines, and tooltips automatically update their contrast colors without requiring a browser refresh.

---

## 13. Autonomous Simulation Engine & Demo Mode

The simulation engine (`backend/app/services/synthetic_simulator.py`) generates realistic sustainable-facility telemetry for demonstrations and offline environments.

```
                      SIMULATION CYCLE (Every 30s)
                                   │
                   Query All Active Organisations
                                   │
                Is Org data_source == 'synthetic'?
                        ├── NO  ──> Skip Organisation
                        └── YES
                                   │
                    Evaluate Demo Mode Enrollment:
                   Is Org enrolled in _demo_orgs?
                        ├── NO  ──> Natural Cadence (10-min anomaly gap)
                        └── YES ──> Demo Cadence (1 anomaly per 30s cycle)
                                   │
                 Filter Enabled Sensors for Org/Module
                                   │
                   Resolve Spatial Generation Targets:
                   - Block-wise: Generate for every FacilityBlock
                   - Civic Wards: Generate for every MunicipalityWard
                   - Org-level: Generate single Reading
                                   │
                Generate Metric Value (Diurnal Curve / Noise)
                        ├── Cumulative (Energy, Water): Monotonic Step
                        ├── Percentage (Waste): 15% - 85% Fill
                        └── Variable (AQI, Temp): Baseline ± Fluctuations
                                   │
                 Write SensorReading to DB (source='synthetic')
                                   │
                    Did this reading fire an anomaly?
                        ├── NO  ──> Cycle Complete
                        └── YES
                                   │
                 Synchronous Pipeline Execution:
                 - Write AnomalyRecord (Status: OPEN)
                 - Generate & Link AIRecommendation
                 - Update Priority Engine Cache
                 - Broadcast Notification & Red Dot
```

### Key Simulator Rules & Parameters
- **Cycle Cadence**: Runs on a monotonic background thread loop with a 30-second interval (`self.interval_seconds = 30`).
- **Zero Backlog Accumulation**: If a cycle takes longer than 30s, missed deadlines are skipped rather than executing rapid catch-up cycles (`synthetic_simulator.py:404-410`).
- **Strict Scope Isolation**: When Demo Mode is active for Organisation A, Organisation B stays completely frozen with zero artificial readings generated.
- **Module Scoping**: When Demo Mode is initiated from `/dashboard/modules/energy`, only energy sensors generate scenario anomalies.
- **Deterministic Scenario Rotation**: Rotates through 9 predefined scenarios:
  1. *Water Supply Leak* (`water` on block)
  2. *Waste Overflow* (`waste` on block)
  3. *Heavy Rainfall* (`rainfall` on ward)
  4. *Drainage Backup* (`sewage_level` on ward)
  5. *Traffic Congestion* (`traffic` on ward)
  6. *Pump Pressure Loss* (`water_flow` on ward)
  7. *Street Light Outage* (`street_lighting` on ward)
  8. *Air Quality Spike* (`air_quality` on org)
  9. *Energy Overload* (`energy` on block)
- **Cumulative Monotonic Progression**: Cumulative sensors (`energy`, `water`) maintain physical location accumulators keyed on `(org_id, block_id, ward_id, sensor_type)` and never decrease during a simulated day.

---

## 14. Simulated Date & "Change Day" System

GreenNexa decouples the application simulation calendar from the physical server clock, allowing operators to test longitudinal features like multi-day forecasts and reporting without waiting weeks.

- **Current Simulated Date**: Stored in the database inside `organisation_sensor_configs.simulated_date` (defaults to `2026-09-20`).
- **Calendar Advancement Flow**:
  1. User clicks **Change Day** in the header `⋯` menu or edits the date in the top pill.
  2. Frontend dispatches `POST /api/v1/simulator/synthetic/change-day` with `{ "days": 1, "organisation_id": orgId }`.
  3. Backend increments `simulated_date` by +1 day (e.g., from `2026-09-20` to `2026-09-21`), updates the day-of-week indicator, and clears cumulative memory caches.
  4. Cumulative daily metrics (kWh, Litres) reset their daily starting values to the baseline, simulating a fresh morning facility startup.
  5. Forecasting models immediately adapt their 24h/7d projection horizons to start from the new date.
  6. Frontend receives the response, updates `localStorage`, and fires the `greennexa_day_changed` event to re-fetch telemetry.

---

## 15. Core & Civic Operational Modules

GreenNexa provides 8 Core Facility Modules and 4 Civic Municipality Modules.

### Detailed Modules Specification

| Module Identifier | Core / Civic | Primary Unit | Metric Nature | Anomaly Rule & Threshold Defaults | Prescriptive Action Generated |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Energy** | Core | kWh | Cumulative | Baseline: 100 kWh, Warn: +15%, Crit: +30% | Inspect high-load HVAC equipment; load-shed non-essential circuits. |
| **2. Water** | Core | Litres (L) | Cumulative | Baseline: 500 L, Warn: +15%, Crit: +30% | Inspect physical plumbing distribution for pipe burst or valve failure. |
| **3. Waste** | Core | % Fill | Bounded (0-100%) | Baseline: 50%, Warn: 80%, Crit: 90% | Dispatch on-demand municipal waste truck; compress compactors. |
| **4. Air Quality** | Core | AQI / ppm | Variable Live | Baseline: 45 AQI, Warn: 100 AQI, Crit: 150 AQI | Increase fresh air damper intake; inspect particulate filtration. |
| **5. Traffic & Parking**| Core | Vehicles/hr | Variable Live | Baseline: 120 veh/h, Warn: +25%, Crit: +50% | Adjust signal phasing; deploy civic traffic management advisory. |
| **6. Assets** | Core | Health Index | Variable (0-100) | Baseline: 95, Warn: <75, Crit: <60 | Schedule preventive electromechanical motor bearing lubrication. |
| **7. Safety** | Core | Score / Incidents| Variable Live | Baseline: 98, Warn: <85, Crit: <70 | Activate emergency response protocol; inspect fire/smoke alarms. |
| **8. Climate** | Core | °C / % / ppm | Variable Live | Baseline: 24°C, Warn: ±4°C, Crit: ±7°C | Modulate chiller plant cooling towers; adjust building envelope airflow. |
| **9. Street Lighting** | Civic | % Operational | Bounded (0-100%) | Baseline: 98%, Warn: <90%, Crit: <80% | Dispatch electrical maintenance crew to replace burned-out luminaires. |
| **10. Roads** | Civic | Condition (0-100)| Variable Live | Baseline: 90, Warn: <70, Crit: <55 | Schedule asphalt pothole patching crew; divert heavy freight transit. |
| **11. Parks** | Civic | Soil Moisture % | Variable Live | Baseline: 65%, Warn: <40%, Crit: <25% | Activate automated municipal sprinkler irrigation in civic gardens. |
| **12. Drainage/Sewage**| Civic | Sump Level % | Bounded (0-100%) | Baseline: 35%, Warn: >75%, Crit: >90% | Activate auxiliary stormwater lift pumps; clear intake grate debris. |

---

## 16. Facility Hierarchy & Spatial Scoping

GreenNexa strictly segregates physical indoor facility spaces from outdoor municipal administrative territories.

```
       STANDARD FACILITY ARCHITECTURE                     MUNICIPALITY CIVIC ARCHITECTURE
       (Hospital, University, School)                        (City Corporation / Council)

                Organisation                                         Organisation
                     │                                            (Municipality Org)
                     │                                                    │
        ┌────────────┴────────────┐                        ┌──────────────┴──────────────┐
        ▼                         ▼                        ▼                             ▼
  FacilityBlock             FacilityBlock           MunicipalityWard              Associated Orgs
   ("Block A")               ("Block B")               ("Ward 01")             (Gov Hospital, College)
        │                         │                        │                             │
  Sensor Readings           Sensor Readings         Sensor Readings                Independent
  (Energy, Water)           (Energy, Water)         (Rainfall, Traffic)          Facility Telemetry
```

### Spatial Aggregation Rules (`backend/app/core/aggregation.py`)
- **Block-Wise Modules** (`BLOCK_WISE_MODULES = {"energy", "water", "waste", "assets"}`): For standard organisations, telemetry is captured and attributed per `FacilityBlock`.
- **Natural-Location Modules** (`NATURAL_LOCATION_MODULES = {"traffic", "parking", "street_lighting", "roads", "parks", "sewage", "rainfall", "water_flow", "water_level"}`): For municipalities, telemetry is captured and attributed per civic `MunicipalityWard`.
- **Whole-Organisation Modules** (`WHOLE_ORG_DEFAULT_MODULES = {"air_quality", "climate", "safety"}`): Attributed to the entire facility campus as a whole.
- **Critical Distinction**: A hospital inpatient ward is stored as a `FacilityBlock` (physical building partition). A city municipal ward is stored as a `MunicipalityWard` (civic geographic zone with census population and area).

---

## 17. Municipality System & Cross-Facility Aggregation

A Municipality in GreenNexa is an `Organisation` created with `facility_type == "municipality"`. It provides high-level regional governance across city infrastructure.

### Unique Municipality Capabilities
1. **Administrative Wards**: Managed via `POST /api/v1/organisations/{id}/wards`. Contains civic metadata: `ward_number`, `ward_name`, `zone`, `population`, and `area_sq_km`.
2. **Associated Government Facilities**:
   - Municipalities can associate existing government facilities (e.g. District Hospital, Government Engineering College, Fire Directorate) via `POST /api/v1/organisations/{id}/associated-government-orgs`.
   - *Government-Only Restriction*: The API strictly verifies `target_org.ownership_type == "GOVERNMENT"`. Private commercial entities cannot be associated with a municipality (`organisations.py:1503-1507`).
   - Stored in `OrganisationSensorConfig.sensor_configs` under the JSON keys `associated_gov_org_ids` and `_municipality_assoc`.
3. **Read-Only Regional Oversight**: The Municipality Administrator can review aggregated telemetry, ward health, and incident alerts across associated facilities, but cannot alter the internal block configurations or credentials of those facilities.

---

## 18. Organisation Onboarding & Modification Lifecycle

Organisation creation is atomic and orchestrated via `POST /api/v1/super-admin/organisations/create-full` (`backend/app/api/v1/super_admin.py:228-470`).

### The 4-Step Registration Process
1. **Step 1: Entity & Campus Identification**
   - Organisation Name, Ownership Type (`GOVERNMENT` or `PRIVATE`).
   - Facility Type (`school`, `college_university`, `hospital`, `municipality`, `industrial_estate`, `public_sector`, `other_facility`).
   - Campus/Facility Name, Address, City, District, State, and unique Org Code.
   - Auto-generated or manual Organisation ID (e.g. `ORG-00028`).
2. **Step 2: Administrator Account Creation**
   - Admin Full Name, Email Address, Contact Phone Number (normalized +91), and Initial Password.
   - Automatically provisions a user record with `role = "ADMIN"`.
3. **Step 3: Spatial Configuration**
   - For standard facilities: List of `FacilityBlock` items (minimum 1 required).
   - For municipalities: List of `MunicipalityWard` items with optional zones and population.
4. **Step 4: Sensor Selection & Threshold Customization**
   - System auto-selects recommended sensors based on `facility_type`.
   - Admin can activate optional sensors and customize baselines, warning deltas (%), and critical deltas (%).
   - Commits all records in a single database transaction.

---

## 19. Master Sensor Catalog & Auto-Selection Engine

The Sensor Catalog (`backend/app/core/sensor_catalog.py`) defines over 30 sensor specifications and rules for automatic preselection during facility onboarding.

### Sensor Preselection Matrix

| Facility Type | Recommended Sensors (Pre-Selected by Default) | Optional Sensors Available |
| :--- | :--- | :--- |
| **School** | Energy, Water, Waste, Temperature, Air Quality, Safety | CO2, Humidity, Occupancy, Dust PM |
| **College / University** | Energy, Water, Waste, Temperature, CO2, Air Quality, Traffic, Parking, Safety | Humidity, Occupancy, Acoustic Sound, Fire/Smoke |
| **Hospital** | Energy, Water, Waste, Temperature, Humidity, CO2, Air Quality, Safety, Assets | Pressure, Flow, Machine Temp, Current/Voltage |
| **Municipality** | Energy, Water, Waste, Air Quality, Traffic, Parking, Street Lighting, Roads, Parks, Sewage, Rainfall, Safety | Water Flow, Water Level, Sewage Level, Dust PM |
| **Industrial Estate** | Energy, Water, Waste, Air Quality, Assets, Safety, Vibration, Pressure, Flow, Machine Temp | RPM, Current/Voltage, Runtime Hours, Gas Leak |
| **Public Sector** | Energy, Water, Waste, Temperature, Air Quality, Traffic, Parking, Safety | CO2, Humidity, Occupancy, Street Lighting |
| **Other / Commercial** | Energy, Water, Waste, Temperature, Air Quality, Safety | Humidity, CO2, Traffic, Parking, Occupancy |

*(Verified in `backend/app/core/sensor_catalog.py:165-245`)*

---

## 20. Database Schema & Entity Architecture

GreenNexa uses SQLAlchemy ORM connected to an underlying SQLite database (configurable to PostgreSQL/MySQL via `.env`). The schema consists of 13 normalized tables.

```
                                DATABASE ENTITY-RELATIONSHIP MAP
                                
      ┌────────────────────────────────────────────────────────┐
      │                                                        │
      │                     organisations                      │
      │   id (PK), name, ownership_type, org_type, is_active   │
      │                                                        │
      └───┬────────────┬─────────────┬─────────────┬───────┬───┘
          │ 1:N        │ 1:N         │ 1:N         │ 1:1   │ 1:N
          ▼            ▼             ▼             ▼       ▼
        users    facility_blocks  municipality_  organis- iot_devices
     id, email,   id, block_id,      wards       ation_    id, device_id,
     hashed_pwd,  block_name,     id, ward_num,  sensor_   api_key_hash,
     role, org_id  is_active        is_active    configs   is_active
          │                                         │
          │ 1:N                                     │
          ▼                                         │
     password_reset_                                │
          otps                                      │
                                                    │
      ┌─────────────────────────────────────────────┴──────────┐
      │ 1:N                     │ 1:N                          │ 1:N
      ▼                         ▼                              ▼
sensor_readings          anomaly_records               ai_recommendations
id, sensor_type,         id, metric, severity,         id, anomaly_id (FK),
value, unit, timestamp,  status, anomaly_score,        summary, action,
is_anomaly, block_id     block_id, ward_id             savings_estimate
```

### Table Definitions & Lifecycles

1. `organisations` (`backend/app/db/models.py:95`): Tenant legal entity. Primary Key: `id` (e.g. `ORG-00001`). Contains location, contact information, facility type, and active status.
2. `users` (`models.py:47`): Authentication accounts. Primary Key: `id`. Links to `organisation_id` (nullable for Super Admin). Stores PBKDF2 hashed password, phone, role (`SUPER_ADMIN` or `ADMIN`), and active status.
3. `facility_blocks` (`models.py:133`): Physical facility divisions (e.g. "Main Wing", "Block A"). Linked to `organisation_id`.
4. `municipality_wards` (`models.py:163`): Civic municipal zones. Linked to `municipality_id` (an organization). Stores `ward_number`, `ward_name`, `population`, `area_sq_km`.
5. `organisation_sensor_configs` (`models.py:201`): Sensor configuration per organisation. Stores `data_source` (`synthetic` or `iot`), `enabled_sensors` (pipe-separated string), `sensor_configs` (JSON containing baselines, thresholds, and associated gov orgs), and `simulated_date`.
6. `sensor_readings` (`models.py:284`): Primary time-series telemetry table. Stores `sensor_type`, `value`, `unit`, `source`, `timestamp`, `is_anomaly`, `anomaly_severity`, `block_id`, and `ward_id`.
7. `anomaly_records` (`models.py:343`): Incident log. Stores `metric`, `value`, `expected_min`, `expected_max`, `severity` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), `status` (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`), `anomaly_score`, and location tags.
8. `ai_recommendations` (`models.py:421`): Prescriptive remediation records. Foreign Key to `anomaly_id`. Stores summary, detailed recommended actions, root causes, estimated kWh/L savings, and implementation status (`PENDING`, `IMPLEMENTED`, `DISMISSED`).
9. `iot_devices` (`models.py:488`): Hardware device registry. Stores `device_id`, PBKDF2 `api_key_hash`, `device_type`, `hardware_model`, and `last_seen_at`.
10. `messages` (`models.py:539`): Internal alert logs and operator communication records.
11. `event_read_states` (`models.py:588`): Unseen notification tracking. Maps `user_id` and `anomaly_id` to determine red-dot indicators.
12. `password_reset_otps` (`models.py:623`): Stores hashed SMS OTPs, expiration timestamps, and verification attempt counts.
13. `platform_state` (`models.py:660`): Stores global platform operational state, including the `platform_data_cleared` latch to prevent automatic reseeding on server restart.

---

## 21. End-to-End Data Flow Diagrams

### A. Autonomous Synthetic Telemetry Flow
```
Synthetic Simulator Background Thread (30s Tick)
  │
  ├── Checks Organisation data_source == 'synthetic'
  ├── Evaluates Diurnal Formula + Random Jitter
  ├── Writes to sensor_readings (is_anomaly=True/False)
  │
  └── IF is_anomaly == True:
        ├── anomaly_detection_service.process_single_reading()
        ├── Writes AnomalyRecord (Status: OPEN)
        ├── Writes linked AIRecommendation
        ├── Emits WebSocket / Updates Priority Engine
        └── Triggers Red-Dot in NotificationContext
```

### B. Hardware IoT Telemetry Flow
```
ESP32 / Wokwi Microcontroller
  │ (HTTP POST with X-Device-ID & X-API-Key Headers)
  ▼
POST /api/v1/iot/sensor-data
  │
  ├── Verify Device Credentials via PBKDF2 Hash Match
  ├── Verify Organisation is_active & data_source == 'iot'
  ├── Prevent Header vs Body ID Spoofing
  ├── Verify Sensor Type is Enabled in Organisation Config
  ├── Write SensorReading Record
  ├── Update Device last_seen_at Timestamp
  │
  └── Synchronous Pipeline Inspection:
        └── anomaly_detection_service.process_single_reading()
```

### C. Incident & Recommendation Resolution Flow
```
Anomaly Detected (Status: OPEN)
  │
  ├── Operator clicks "Acknowledge" on UI
  │     └── PATCH /api/v1/anomalies/{id}/acknowledge
  │           └── Status becomes ACKNOWLEDGED
  │
  ├── Operator takes physical remediation action
  │     └── PATCH /api/v1/anomalies/{id}/resolve
  │           └── Status becomes RESOLVED (Removed from active alarms)
  │
  └── Operator confirms recommendation implementation
        └── PATCH /api/v1/recommendations/{id}/status (status: IMPLEMENTED)
```

---

## 22. Hardware IoT Telemetry Ingestion System

GreenNexa includes an enterprise-grade IoT ingestion gateway (`backend/app/api/v1/iot.py`) supporting real hardware devices such as ESP32, ESP8266, Arduino with Ethernet/WiFi, and Wokwi virtual simulators.

### Ingestion Authentication & Security Protocol
- **Endpoint**: `POST /api/v1/iot/sensor-data` (`backend/app/api/v1/iot.py:112`)
- **Required HTTP Headers**:
  - `X-Device-ID`: Unique hardware identifier (e.g. `ESP32-BLDG-A-01`).
  - `X-API-Key`: Plaintext device API secret key.
- **Header Authentication**: The backend verifies `X-API-Key` against the salted PBKDF2 hash stored in `iot_devices.api_key_hash`.
- **Hardware Mode Enforcement**: If the target organisation has `data_source == 'synthetic'`, the gateway rejects incoming telemetry with `HTTP 409 Conflict` ("Organisation is not configured for IoT data").
- **Spoofing Guard**: The gateway ensures the header `X-Device-ID` strictly matches the `device_id` in the JSON body.
- **Payload Schema**:
  ```json
  {
    "device_id": "ESP32-BLDG-A-01",
    "timestamp": "2026-09-27T14:30:00Z",
    "readings": [
      { "sensor_type": "energy", "value": 142.8, "unit": "kWh" },
      { "sensor_type": "temperature", "value": 26.4, "unit": "°C" }
    ]
  }
  ```
- **Post-Ingestion Pipeline**: As soon as records are written to `sensor_readings`, each reading is evaluated synchronously through `anomaly_detection_service.process_single_reading(...)`.

---

## 23. AI & Machine Learning Engine

GreenNexa deploys a multi-layered analytical and predictive pipeline combining statistical methods, time-series forecasting, and unsupervised machine learning (`backend/app/services/`).

```
                    ANOMALY DETECTION PIPELINE
                                │
                        New Sensor Reading
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
    LAYER 1                 LAYER 2                 LAYER 3
Super Admin Rules      Statistical Z-Score     IsolationForest ML
(Threshold Deltas)      (Rolling 3-Sigma)     (Unsupervised Outlier)
        │                       │                       │
Warn: > Baseline + W%    |Z| > 3.0 Standard      Outlier on 8-Feature
Crit: > Baseline + C%       Deviations                 Vector
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                       Unified Arbiter:
            Determines Severity (CRITICAL, HIGH, MED, LOW)
            Persists AnomalyRecord & Generates AIRecommendation
```

### Machine Learning Algorithms & Mathematical Formulations

1. **Time-Series Forecasting (`forecasting.py`)**
   - *Algorithm*: Statsmodels `ExponentialSmoothing` (Holt-Winters with additive 24-hour diurnal seasonality).
   - *Fallbacks*: Linear Holt Exponential Smoothing -> Simple Exponential Smoothing (`SimpleExpSmoothing`) -> Historical Mean Baseline.
   - *Horizon Bounds*: Produces forecasts across 24 Hours, 7 Days, 15 Days, and 30 Days. Strictly verifies historical point density (requires at least 3 points for preliminary trend, 24+ for diurnal modeling).
   - *Uncertainty Modeling*: Calculates a dynamic 95% Confidence Interval using rolling sample standard deviation: $\hat{y}_t \pm 1.96 \cdot \sigma_t$.

2. **Unsupervised Outlier Detection (`anomaly_ml_service.py`)**
   - *Algorithm*: Scikit-Learn `IsolationForest` (`n_estimators=100`, `contamination=0.03`, `random_state=42`).
   - *Feature Vector*: 8 engineered dimensions:
     1. Current reading value
     2. Rolling 1-hour average
     3. Rolling 24-hour average
     4. Rate-of-change (first derivative $\Delta v / \Delta t$)
     5. Hour of day (normalized $h / 24$)
     6. Day of week (normalized $d / 7$)
     7. Deviation from baseline ($v - \text{baseline}$)
     8. Percentage deviation from baseline ($|(v - \text{baseline}) / \text{baseline}|$)

3. **Statistical Deviation Detection (`anomaly_detection.py`)**
   - *Algorithm*: Rolling Z-Score evaluation:
     $$Z = \frac{x_t - \mu_{24h}}{\sigma_{24h}}$$
   - *Threshold*: Flags statistical anomalies when $|Z| \ge 3.0$ standard deviations from the rolling mean.

---

## 24. Multilingual Conversational Assistant (Gemini)

The conversational assistant (`GreenNexaAssistant.tsx` and `backend/app/ai/assistant/`) provides hands-free natural language querying over facility operations.

### Multilingual Natural Language Understanding (NLU)
The NLU engine (`backend/app/ai/assistant/nlu.py`) detects intent across 4 localized languages:
1. **English**: "What is today's total energy consumption?"
2. **Hinglish**: "Aaj ka water leakage kidhar hua hai?"
3. **Odia Script (ଓଡ଼ିଆ)**: "କେଉଁ ବ୍ଲକରେ ଅଧିକ ପାଣି ବ୍ୟବହାର ହେଉଛି?"
4. **Roman Odia**: "ko block re adhika energy usage hauchhi?"

### Gemini Model & Tool Calling Architecture
- **Model**: `gemini-2.5-flash` via the official Google GenAI SDK (`google-genai`). Server-side API key handling ensures the key is never exposed to the browser.
- **Tenant Isolation Barrier**: An organisation `ADMIN` cannot query platform-wide metrics. Attempting cross-organisation queries returns a localized denial message (`service.py:115-130`).
- **Tool Registry (`backend/app/ai/assistant/gemini_tools.py`)**:
  - *Tenant Tools (10)*: `get_current_metrics`, `get_active_anomalies`, `get_forecast`, `get_block_comparison`, `get_recommendations`, `get_facility_status`, `run_energy_scenario`, `run_water_scenario`, `run_waste_scenario`, `run_traffic_scenario`.
  - *Platform Tools (5, Super Admin Only)*: `get_platform_summary`, `get_organisation_list`, `count_organisations_by_facility_type`, `get_total_admins`, `compare_organisations`.
- **Voice Integration**: Implements the Web Speech Recognition API for speech-to-text input and `SpeechSynthesisUtterance` for localized spoken audio responses.

---

## 25. What-If Predictive Scenario Simulator

Embedded directly into the AI Assistant and analytical tools (`backend/app/ai/assistant/gemini_tools.py:270-430`), the What-If Engine simulates the operational impact of facility management decisions.

1. **Energy Scenario (`run_energy_scenario`)**:
   - *Input*: Percentage reduction in HVAC setpoint or load shedding percentage (e.g. `reduction_pct: 15`).
   - *Calculation*: Projects daily kWh saved, calculated utility cost reduction in INR (₹8.50/kWh baseline), and estimated metric tons of avoided $\text{CO}_2$ emissions ($0.82 \text{ kg }\text{CO}_2/\text{kWh}$).
2. **Water Scenario (`run_water_scenario`)**:
   - *Input*: Fixture aerator retrofit percentage or cooling tower cycle concentration adjustment.
   - *Calculation*: Computes daily kilolitres conserved and reservoir supply extension in operational days.
3. **Waste Scenario (`run_waste_scenario`)**:
   - *Input*: On-site composting and source-segregation compliance rate.
   - *Calculation*: Computes reduction in municipal landfill tonnage and diversion percentage.
4. **Traffic Scenario (`run_traffic_scenario`)**:
   - *Input*: Staggered workplace shift hours or auxiliary parking redirect percentage.
   - *Calculation*: Estimates peak intersection queue length reduction and vehicle idling fuel savings.

*(Disclaimer: Output is explicitly labeled as a predictive scenario model based on current baselines, not a physical contract guarantee).*

---

## 26. Anomaly & Alert System

GreenNexa tracks operational anomalies through a formal, auditable lifecycle.

```
       DETECTED
  (Rule / Z-Score / ML)
          │
          ▼
        OPEN ───────────────> DISMISSED
          │              (Marked as False Alarm)
          ▼
    ACKNOWLEDGED
(Operator Notified)
          │
          ▼
       RESOLVED
 (Remediation Complete)
```

### Anomaly Lifecycle States & API Handlers
- `OPEN` (`AnomalyRecord.STATUS_OPEN = "OPEN"`): Anomaly newly detected by simulator, IoT, or ML. Triggers unread red-dot indicators on navigation bars.
- `ACKNOWLEDGED` (`PATCH /api/v1/anomalies/{id}/acknowledge`): An operator has inspected the incident and taken ownership.
- `RESOLVED` (`PATCH /api/v1/anomalies/{id}/resolve`): The physical fault has been corrected. Clears active status from priority engine calculations.
- `DISMISSED` (`PATCH /api/v1/anomalies/{id}/dismiss`): Operator flags the reading as a known false positive or planned maintenance event.
- **Persistence Invariant**: GreenNexa deliberately **does not** auto-resolve anomalies on the arrival of subsequent normal readings (`synthetic_simulator.py:899-904`). Open anomalies require explicit human operator review.

---

## 27. Anomaly Priority Engine

The Priority Engine (`backend/app/services/priority_engine.py`) prevents alert fatigue in large operational control rooms.

### Activation Rules & Prioritization Logic
- **Activation Threshold**: The engine activates **only when 3 or more active anomalies** (`STATUS_OPEN` or `STATUS_ACKNOWLEDGED`) exist simultaneously for an organisation (`priority_engine.py:85-95`).
- **Below Threshold**: If fewer than 3 active anomalies exist, the engine returns `is_active = False` with the message: *"Priority engine activates when 3 or more active anomalies are detected. Currently: N active."*
- **Scoring & Ranking Formula**:
  $$\text{Priority Score} = (\text{Severity Weight}) \times 40 + (\text{Deviation Pct}) \times 35 + (\text{Critical Module Weight}) \times 25$$
  - *Severity Weights*: Critical = 1.0, High = 0.7, Medium = 0.4, Low = 0.1.
  - *Critical Modules*: Energy, Water Supply, and Healthcare Safety carry higher weights than ambient noise or parking.
- **Output**: Returns the single highest-priority anomaly requiring immediate operator intervention, accompanied by an explainability rationale.

---

## 28. Event Notification & "Red-Dot" Tracking Engine

The Red-Dot Notification Engine (`frontend/src/context/NotificationContext.tsx` and `backend/app/api/v1/notifications.py`) ensures operators never miss critical facility incidents.

- **Unseen Tracking**: Evaluated against the `event_read_states` database table. A red dot appears on navigation items whenever `AnomalyRecord` entries have not been acknowledged or viewed by the logged-in user.
- **Granular Scoping**:
  - *Module Red Dots*: Displayed on sidebar items (e.g. Energy shows a red dot if an unread anomaly exists on an energy sensor).
  - *Block Red Dots*: Displayed in facility block selectors (`module_blocks[module][block_id]`).
  - *Ward Red Dots*: Displayed in municipal ward selectors (`wards[ward_id]`).
- **Clearing Mechanism**: Clicking into an anomaly card, acknowledging the alert, or viewing the module dispatches `POST /api/v1/notifications/mark-read`, immediately extinguishing the red dot for that item across all client tabs.

---

## 29. Reporting & Audit Export Engine

The Reporting Engine (`backend/app/services/reporting.py`) generates audit-ready compliance documentation.

### Supported Formats & Report Types
- **Export Formats**: CSV (`text/csv; charset=utf-8`) and PDF (`application/pdf`).
- **Report Types**:
  1. `dashboard` — Executive summary, active KPIs, and incident rollups.
  2. `energy` — Granular kWh telemetry, baseline variance, and peak load tables.
  3. `water` — Litres consumed, flow surges, and leakage audit logs.
  4. `waste` — Bin fill percentages, overflow incidents, and collection history.
  5. `environmental` — Ambient temperature, relative humidity, and CO2 compliance.
  6. `anomalies` — Complete incident registry with detection scores and resolution timestamps.
  7. `recommendations` — AI recommendations with estimated cost savings.
  8. `forecast` — Multi-day projected load distributions with 95% confidence bands.
  9. `iot` — Raw device hardware logs and transmission timestamps.
- **Actual CSV Headers Example (Sensor Report)**:
  `["Timestamp", "Organisation ID", "Sensor Metric", "Value", "Unit", "Data Source", "Anomaly Detected", "Severity"]`
- **PDF Generation**: Compiled using ReportLab with clean tabular styles, official letter page dimensions, summary KPIs, and audit disclaimers.

---

## 30. Database Storage Governance & Compaction

The Manage Storage subsystem (`backend/app/api/v1/super_admin.py:1996-2128` and `/super-admin/storage`) gives Super Admins exact visibility into disk footprint and database growth.

```
                  MANAGE STORAGE GOVERNANCE
                              │
       ┌──────────────────────┴──────────────────────┐
       ▼                                             ▼
PHYSICAL STORAGE METRICS                     LOGICAL ATTRIBUTION
- File: greennexa_test.db                    - Deterministic Record Footprint:
- Real DB File Size (os.path.getsize)          • Sensor Reading: 128 bytes/row
- OS Disk Allocation (Total / Free / %)        • Anomaly Record: 256 bytes/row
                                               • Recommendation: Text + 128 bytes
                                               • Blocks & Wards: 96 bytes/row
                                               • IoT Devices: 128 bytes/row
                                             - Grouped by Government vs Private
                                             - Percentage Share per Organisation
                              │
                              ▼
                 SQLite Disk Compaction (VACUUM)
                 - Executed during Clear Data
                 - Releases unused pages back to host OS
```

### Physical vs Logical Attribution Distinction
- **Physical Size**: Represents the actual byte size of the SQLite database file on the server filesystem (`get_db_physical_size_bytes()`).
- **Logical Attribution**: In SQLite, tables are shared across tenants in a single file. GreenNexa calculates deterministic logical storage by auditing the exact row footprint and string lengths of every record owned by an organisation.
- **Disk Reclamation**: Executing an Admin Clear Data or Super Admin Clear All Data triggers `safe_vacuum_sqlite(engine)`, executing the `VACUUM` command to reclaim freed disk pages and shrink the physical `.db` file.

---

## 31. Complete API Endpoint Map

| Category | HTTP Method | Endpoint Path | Role Allowed | Purpose |
| :--- | :---: | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/v1/auth/login` | Public | Authenticate user, check org type, issue JWT |
| **Auth** | `GET` | `/api/v1/auth/me` | Logged In | Get current authenticated user profile |
| **Auth** | `POST` | `/api/v1/auth/logout` | Logged In | Log out and stop organisation simulator |
| **Auth** | `POST` | `/api/v1/auth/forgot-password/request` | Public | Request SMS OTP for password reset |
| **Auth** | `POST` | `/api/v1/auth/forgot-password/verify-otp` | Public | Verify 6-digit SMS OTP |
| **Auth** | `POST` | `/api/v1/auth/forgot-password/reset-password` | Public | Set new password with verified OTP token |
| **Super Admin** | `GET` | `/api/v1/super-admin/overview` | `SUPER_ADMIN` | Platform metrics and organisation matrix |
| **Super Admin** | `POST` | `/api/v1/super-admin/organisations/create-full` | `SUPER_ADMIN` | Atomic 4-step organisation & admin creation |
| **Super Admin** | `GET` | `/api/v1/super-admin/users` | `SUPER_ADMIN` | List all platform administrators and users |
| **Super Admin** | `POST` | `/api/v1/super-admin/verify-confirmation-password`| `SUPER_ADMIN` | Verify confirmation password for destructive tasks |
| **Super Admin** | `POST` | `/api/v1/super-admin/users/{id}/reset-password` | `SUPER_ADMIN` | Admin password reset with confirmation secret |
| **Super Admin** | `POST` | `/api/v1/super-admin/clear-all-data` | `SUPER_ADMIN` | Complete platform reset (preserves superadmin) |
| **Super Admin** | `GET` | `/api/v1/super-admin/storage` | `SUPER_ADMIN` | Real physical DB size & org logical breakdown |
| **Organisations**| `GET` | `/api/v1/organisations` | Logged In | List accessible organisations |
| **Organisations**| `POST` | `/api/v1/organisations/{id}/clear-data` | `ADMIN` (Own) | Clear organisation operational telemetry |
| **Organisations**| `GET` | `/api/v1/organisations/{id}/blocks` | Logged In | List facility blocks |
| **Organisations**| `POST` | `/api/v1/organisations/{id}/blocks` | `ADMIN` (Own) | Add new facility block |
| **Organisations**| `GET` | `/api/v1/organisations/{id}/wards` | Logged In | List municipality administrative wards |
| **Organisations**| `POST` | `/api/v1/organisations/{id}/wards` | `ADMIN` (Muni) | Add new municipality administrative ward |
| **Organisations**| `POST` | `/api/v1/organisations/{id}/associated-government-orgs` | `ADMIN` (Muni) | Associate existing Government facility |
| **Dashboard** | `GET` | `/api/v1/dashboard/kpis` | Logged In | Get real-time KPIs and aggregated metrics |
| **Dashboard** | `GET` | `/api/v1/dashboard/waveform` | Logged In | Continuous 24h diurnal timeseries points |
| **Forecast** | `GET` | `/api/v1/forecast/{sensor_type}` | Logged In | Holt-Winters time-series forecast with 95% CI |
| **Anomalies** | `GET` | `/api/v1/anomaly/all` | Logged In | Filtered list of operational anomalies |
| **Anomalies** | `PATCH` | `/api/v1/anomaly/{id}/acknowledge` | Logged In | Move anomaly to ACKNOWLEDGED |
| **Anomalies** | `PATCH` | `/api/v1/anomaly/{id}/resolve` | Logged In | Move anomaly to RESOLVED |
| **Anomalies** | `PATCH` | `/api/v1/anomaly/{id}/dismiss` | Logged In | Move anomaly to DISMISSED |
| **Priority** | `GET` | `/api/v1/priority-engine/high-priority-anomaly` | Logged In | Evaluate top urgent anomaly (active at 3+ events) |
| **AI Assistant** | `POST` | `/api/v1/ai/chat` | Logged In | Multilingual Gemini chat with tool execution |
| **AI Assistant** | `GET` | `/api/v1/ai/suggestions` | Logged In | Contextual starter prompts |
| **IoT Gateway** | `POST` | `/api/v1/iot/sensor-data` | Device Auth | Ingest hardware sensor readings |
| **IoT Gateway** | `POST` | `/api/v1/iot/devices` | Logged In | Register new hardware device and issue key |
| **Simulator** | `POST` | `/api/v1/simulator/synthetic/start` | Logged In | Start simulator thread / enable demo mode |
| **Simulator** | `POST` | `/api/v1/simulator/synthetic/stop` | Logged In | Stop simulator thread / disable demo mode |
| **Simulator** | `POST` | `/api/v1/simulator/synthetic/change-day` | Logged In | Advance simulation calendar (+1 day) |
| **Reports** | `GET` | `/api/v1/reports/{report_type}` | Logged In | Download CSV or ReportLab PDF audit report |

---

## 32. Frontend State Management Architecture

GreenNexa manages client-side application state through 6 specialized React Context providers:

1. **`AuthContext` (`frontend/src/context/AuthContext.tsx`)**:
   - Manages `user`, JWT `token`, `activeOrgId`, and `currentOrg`.
   - Injects credentials into all API requests and synchronizes active tenant switches across routes.
2. **`DemoContext` (`frontend/src/context/DemoContext.tsx`)**:
   - Manages `demoModeActive`, `activeDemoModules`, `simulatedDate`, and `formattedDate`.
   - Maintains a 30-second cycle timer (`simElapsedSeconds: 0–29`) that persists across Next.js route transitions.
3. **`DashboardStyleContext` (`frontend/src/context/DashboardStyleContext.tsx`)**:
   - Manages active presentation layout (`EXECUTIVE`, `OPERATIONS`, `ANALYTICS`, `COMMAND_CENTER`).
   - Persists style preferences per organisation in `localStorage`.
4. **`ThemeContext` (`frontend/src/context/ThemeContext.tsx`)**:
   - Manages Day/Night mode and the 6 Color Themes (`emerald`, `ocean-blue`, `indigo`, `teal`, `graphite`, `amber`).
   - Injects `data-theme` and `data-color-theme` attributes directly into the DOM root.
5. **`NotificationContext` (`frontend/src/context/NotificationContext.tsx`)**:
   - Polls `/api/v1/notifications/unread` every 15 seconds.
   - Maintains unread status mappings across modules, blocks, and wards to drive red alert dots.
6. **`ToastContext` (`frontend/src/context/ToastContext.tsx`)**:
   - Dispatches floating success, warning, and error alerts with auto-dismiss timers.

---

## 33. Security Architecture & Multi-Tenant Isolation

### Technical Security Controls
1. **Multi-Tenant Data Isolation**: Every database query for an operational model (`SensorReading`, `AnomalyRecord`, `AIRecommendation`, `FacilityBlock`, `IoTDevice`) strictly enforces `WHERE organisation_id = :target_org_id`. Cross-tenant data leakage is prevented at the ORM layer.
2. **Role Barrier**: Endpoints requiring administrative elevation use the dependency `require_roles(User.ROLE_SUPER_ADMIN)`. Attempts by normal admins to access platform management return `HTTP 403 Forbidden`.
3. **Destructive Action Protection**: Reset Password and Clear All Data require the product owner confirmation secret, preventing unauthorized or accidental platform deletion.
4. **Hardware Spoofing Prevention**: The IoT gateway verifies salted PBKDF2 API key hashes and validates that `X-Device-ID` headers match payload device identifiers.
5. **Secret Redaction**: Environment secrets, JWT keys, and Gemini API tokens are maintained strictly on the server and are never exposed via API responses or frontend client bundles.

---

## 34. Implemented vs Intended Feature Matrix

To maintain rigorous technical integrity, the table below delineates fully working features from design placeholders.

| System Capability | Status | Implementation Evidence |
| :--- | :---: | :--- |
| **JWT Authentication & Role Gating** | **IMPLEMENTED** | `backend/app/api/v1/auth.py`, `dependencies.py` |
| **Gov vs Private Org Type Login Barrier** | **IMPLEMENTED** | `backend/app/api/v1/auth.py:86-102` |
| **Super Admin Platform Overview & Org Matrix** | **IMPLEMENTED** | `backend/app/api/v1/super_admin.py:125-225` |
| **Atomic 4-Step Org & Admin Creation Wizard** | **IMPLEMENTED** | `backend/app/api/v1/super_admin.py:228-470` |
| **Administrative Password Reset with Secret** | **IMPLEMENTED** | `backend/app/api/v1/super_admin.py:1154-1204` |
| **Self-Service Phone SMS OTP Password Reset** | **IMPLEMENTED** | `backend/app/api/v1/auth.py:180-290` |
| **Admin Clear Data (Org Scoped)** | **IMPLEMENTED** | `backend/app/api/v1/organisations.py:1306-1376` |
| **Super Admin Clear All Data (Double Confirm)**| **IMPLEMENTED** | `backend/app/api/v1/super_admin.py:1868-1979` |
| **Storage Governance & SQLite VACUUM** | **IMPLEMENTED** | `backend/app/api/v1/super_admin.py:1996-2128` |
| **Header ⋯ Options Menu** | **IMPLEMENTED** | `frontend/src/components/layout/Header.tsx:281-560` |
| **4 Adaptable Dashboard Styles** | **IMPLEMENTED** | `frontend/src/lib/dashboardStyles.ts` |
| **6 Theme Colors + Day/Night Mode** | **IMPLEMENTED** | `frontend/src/context/ThemeContext.tsx` |
| **Autonomous 30s Simulation Engine** | **IMPLEMENTED** | `backend/app/services/synthetic_simulator.py` |
| **Simulated Date & "Change Day" System** | **IMPLEMENTED** | `backend/app/services/synthetic_simulator.py:470-480` |
| **8 Core Facility Operational Modules** | **IMPLEMENTED** | `frontend/src/app/dashboard/modules/` |
| **4 Civic Municipality Modules** | **IMPLEMENTED** | `frontend/src/app/dashboard/modules/` |
| **Facility Block vs Municipality Ward Division**| **IMPLEMENTED** | `backend/app/core/aggregation.py` |
| **Gov-Only Municipality Org Association** | **IMPLEMENTED** | `backend/app/api/v1/organisations.py:1453-1550` |
| **Sensor Preselection Rules by Facility Type** | **IMPLEMENTED** | `backend/app/core/sensor_catalog.py` |
| **Hardware IoT Ingestion Gateway** | **IMPLEMENTED** | `backend/app/api/v1/iot.py:112-208` |
| **Holt-Winters Multi-Horizon Time-Series AI** | **IMPLEMENTED** | `backend/app/services/forecasting.py` |
| **Tri-Layer Anomaly Detection (Rules, Z, ML)** | **IMPLEMENTED** | `backend/app/services/anomaly_detection.py` |
| **Anomaly Priority Engine (3+ Active Trigger)**| **IMPLEMENTED** | `backend/app/services/priority_engine.py` |
| **Unread Event Notification & Red-Dot Engine** | **IMPLEMENTED** | `frontend/src/context/NotificationContext.tsx` |
| **Multilingual AI Assistant (Gemini 2.5 Tools)**| **IMPLEMENTED** | `backend/app/ai/assistant/service.py` |
| **Voice Speech Input & Localized Speech Output**| **IMPLEMENTED** | `frontend/src/components/ai/GreenNexaAssistant.tsx` |
| **What-If Predictive Scenario Simulator** | **IMPLEMENTED** | `backend/app/ai/assistant/gemini_tools.py` |
| **CSV & ReportLab PDF Export Service** | **IMPLEMENTED** | `backend/app/services/reporting.py` |
| **Interactive 3D BIM/CAD Digital Twin** | **PLACEHOLDER** | Visual mock components in frontend; no 3D rendering pipeline. |
| **Automated Edge Firmware OTA Updates** | **PLACEHOLDER** | UI only; firmware delivery endpoints are not implemented. |

---

## 35. Known Constraints, System Risks & Architectural Boundaries

1. **Single-File SQLite Database**:
   - *Constraint*: GreenNexa defaults to a local SQLite database (`greennexa_test.db`). While fast and self-contained, SQLite serializes write transactions, which can cause lock contention under high-frequency IoT streaming.
   - *Recommendation*: Transition to a dedicated PostgreSQL instance in high-scale production deployments.
2. **Logical Storage Attribution Approximation**:
   - *Constraint*: SQLite allocates storage in unified disk pages. Per-organisation storage attribution is calculated deterministically from raw record schemas and string lengths rather than low-level filesystem page partitioning.
3. **Synthetic Anomaly Cadence in Demo Mode**:
   - *Constraint*: To ensure predictable live product demonstrations, Demo Mode enforces exactly one scenario anomaly every 30 seconds. In real production IoT mode, anomalies depend strictly on incoming physical sensor telemetry.
4. **Historical Point Density for Statistical Forecasting**:
   - *Constraint*: Holt-Winters additive diurnal forecasting requires continuous 24-hour historical readings. If a newly created facility has only 2 or 3 readings, the engine gracefully falls back to linear interpolation and mean baselines.

---

## 36. Test Suite Inventory & Quality Assurance Report

GreenNexa maintains 48 comprehensive automated backend test suites located in `backend/tests/`:

1. `test_admin_sensor_config.py` — Verifies tenant sensor threshold updates.
2. `test_ai_assistant.py` — Validates assistant intent extraction and role barriers.
3. `test_anomaly_detector.py` — Tests rule-based and Z-score thresholding.
4. `test_anomaly_lifecycle_and_recommendations.py` — Tests open -> acknowledged -> resolved flows.
5. `test_api.py` — Core API router and health check validation.
6. `test_auth.py` — Token issuance, role enforcement, and invalid login handling.
7. `test_block_anomaly_recommendation_sync.py` — Ensures block spatial IDs attach across records.
8. `test_clear_data.py` — Validates tenant-scoped operational clear.
9. `test_clear_data_restart_regression.py` — Confirms platform cleared state survives restarts.
10. `test_clear_data_simulator_reset.py` — Confirms simulator state resets on data clearing.
11. `test_dashboard.py` — Tests KPI aggregation and waveform generators.
12. `test_dashboard_style.py` — Verifies layout resolution and capability rules.
13. `test_demo_endpoints.py` — Tests simulation control endpoints.
14. `test_demo_mode_architecture.py` — Confirms tenant scope isolation in demo mode.
15. `test_demo_simulation_and_deactivation.py` — Tests 30s cadence and clean shutdown.
16. `test_facility_blocks.py` — Tests block CRUD and duplicate name prevention.
17. `test_fast_three_bugs.py` — Regression tests for password reset persistence and verification.
18. `test_fast_three_features.py` — Validates confirmation password and storage endpoints.
19. `test_final_bug_responsive_pass.py` — Tests responsive API payload handling.
20. `test_final_implementation_pass.py` — General integration test across subsystems.
21. `test_final_root_cause_fixes.py` — Validates diurnal progression and anomaly persistence.
22. `test_final_scope_and_cadence.py` — Tests round-robin scenario targeting.
23. `test_forecast.py` — Tests Statsmodels forecasting and 95% confidence intervals.
24. `test_gemini_integration.py` — Tests Gemini tool declarations and fallback handlers.
25. `test_greennexa_final_all_bugs.py` — Comprehensive regression test suite.
26. `test_greennexa_final_regression.py` — End-to-end platform regression suite.
27. `test_iot.py` — Tests hardware ingestion, authentication, and duplicate rejection.
28. `test_messages.py` — Tests message threads and unread count aggregation.
29. `test_ml_implementation.py` — Tests Scikit-Learn IsolationForest feature engineering.
30. `test_municipality_extension.py` — Tests municipal civic ward operations.
31. `test_municipality_oversight_read.py` — Tests cross-facility read-only oversight.
32. `test_municipality_ward_civic_suite.py` — Tests ward metrics and population analysis.
33. `test_organisation_ownership.py` — Tests Government vs Private validation rules.
34. `test_organisations.py` — Tests basic organisation CRUD.
35. `test_phase10_anomalies_recommendations.py` — Tests recommendation generation.
36. `test_recommender.py` — Tests prescriptive savings calculations.
37. `test_reports.py` — Tests CSV formatting and ReportLab PDF document compilation.
38. `test_sensor_auto_selection.py` — Tests sensor catalog preselection rules.
39. `test_sensor_config.py` — Tests baseline and threshold validation.
40. `test_simulator.py` — Tests synthetic data generation formulas.
41. `test_super_admin.py` — Tests Super Admin role protection.
42. `test_super_admin_org_edit.py` — Tests multi-step organisation editing.
43. `test_targeted_bug_fixes.py` — Tests password reset persistence regressions.
44. `test_task_spec_acceptance.py` — Specification acceptance test suite.
45. `test_timeseries_waveform_api.py` — Tests continuous waveform interpolation.
46. `test_unseen_red_dot_system.py` — Tests event read states and red dot logic.

---

## 37. End-to-End Operational Lifecycle Story

1. **Platform Deployment & Super Admin Setup**: The platform initializes with an empty database or seeded demo entities. The Super Admin logs in via the platform portal, accessing the full overview.
2. **Facility Onboarding**: The Super Admin uses the multi-step registration wizard to create a new tenant (e.g. *Kalinga Institute of Medical Sciences*). The facility is classified as a Government Hospital, administrative blocks (Emergency Wing, ICU, Outpatient) are registered, an Admin account is created, and recommended healthcare sensors (Energy, Water, Medical Waste, Air Quality) are auto-provisioned with standard baselines.
3. **Data Ingestion Begins**:
   - *Synthetic Mode*: The simulator thread activates, producing realistic diurnal cumulative curves for energy and water and bounded percentages for waste.
   - *Physical IoT Mode*: Real ESP32 microcontrollers authenticate using device API keys via HTTP headers, streaming physical readings to `/api/v1/iot/sensor-data`.
4. **Real-Time Detection & ML Pipeline**: Telemetry streams are written to the database. The tri-layer detection engine continuously monitors readings against configured threshold deltas, 3-sigma rolling statistical standard deviations, and an unsupervised `IsolationForest` ML model.
5. **Incident Generation & AI Recommendation**: A sudden cooling pump failure triggers a critical energy surge. The detection engine flags the anomaly, records an `AnomalyRecord`, and automatically generates a prescriptive `AIRecommendation` outlining root causes (e.g., *Faulty compressor motor bearing*) and estimated electricity cost savings.
6. **Alert Notification & Dispatch**: The unread event tracking engine flags the anomaly in `event_read_states`. A glowing red alert dot appears on the sidebar under **Modules → Energy** and on the **Anomalies** badge.
7. **Operator Intervention**: The facility manager logs into the dashboard, selects the **Operations Style** for dense visibility, inspects the active anomaly, and clicks **Acknowledge**. They review the AI Assistant’s What-If analysis, dispatch maintenance to replace the bearing, and click **Resolve**.
8. **Forecasting & Compliance Audit**: The sustainability officer opens `/forecast` to review projected 7-day load distributions, runs a scenario analysis in the AI Assistant, and exports a signed PDF compliance report for municipal regulatory review.

---

## 38. Executive & Investor Presentation Summary

- **One-Sentence Vision**: *GreenNexa is an enterprise-grade, multi-tenant intelligence platform that unifies IoT telemetry, machine learning, and conversational AI to automate sustainability, resource conservation, and incident response across campuses and smart cities.*
- **The Core Problem**: Modern institutional facilities and municipalities operate in fragmented silos—energy, water, waste, and municipal infrastructure are managed via separate systems with zero predictive intelligence, resulting in delayed leak detection, severe resource wastage, and manual compliance reporting.
- **The Solution**: A single, unified operational intelligence platform that integrates hardware IoT and autonomous simulation, detects anomalies in real-time using statistical ML, forecasts multi-horizon consumption trends, and empowers operators through a localized, multilingual voice AI Assistant.
- **Key Differentiating Pillars**:
  1. *Civic-Aware Multi-Tenancy*: Bridges private facilities with municipal city corporations, allowing municipal oversight of associated government bodies while preserving tenant isolation.
  2. *Tri-Layer Detection & Priority Engine*: Combines deterministic thresholds, rolling statistical Z-scores, and Scikit-Learn unsupervised outlier models to prevent alert fatigue.
  3. *Voice-Enabled Multilingual AI*: Native conversational support across English, Hinglish, Odia, and Roman Odia grounded with 15 domain tools and What-If scenario models.
  4. *Adaptive Presentation Styles*: Instantly transforms layout density between Executive, Operations, Analytics, and Command Center modes without altering underlying telemetry.
- **Technology Stack**:
  - *Frontend*: Next.js 14 (App Router), React 18, Lucide Icons, Vanilla CSS Architecture (Day/Night & 6 Color Themes).
  - *Backend*: Python 3.11+, FastAPI, SQLAlchemy ORM, Pydantic v2.
  - *AI / ML*: Google GenAI SDK (Gemini 2.5 Flash), Statsmodels (Holt-Winters), Scikit-Learn (IsolationForest), NumPy, Pandas.
  - *Database & Storage*: SQLite / PostgreSQL, ReportLab (PDF compilation), PBKDF2 SHA-256 cryptographic security.

---

## 39. Code Traceability Index

For rapid auditing, all major system capabilities are grounded in the following primary source files:

| Subsystem | Primary Source File | Primary Symbols / Functions |
| :--- | :--- | :--- |
| **Authentication Router** | `backend/app/api/v1/auth.py` | `login`, `get_current_user_profile`, `logout` |
| **Super Admin Router** | `backend/app/api/v1/super_admin.py` | `create_full_organisation`, `reset_user_password`, `super_admin_clear_all_data`, `get_platform_storage_overview` |
| **Organisation Router** | `backend/app/api/v1/organisations.py` | `create_facility_block`, `create_municipality_ward`, `clear_organisation_operational_data`, `associate_government_org_with_municipality` |
| **Dashboard Router** | `backend/app/api/v1/dashboard.py` | `get_dashboard_kpis`, `get_timeseries_waveform` |
| **IoT Ingestion Gateway** | `backend/app/api/v1/iot.py` | `_authenticate_iot_device`, `ingest_sensor_data`, `register_device` |
| **Forecasting Engine** | `backend/app/services/forecasting.py` | `ForecastingService.generate_forecast`, `_fit_statsmodels_model` |
| **Anomaly Detection Pipeline**| `backend/app/services/anomaly_detection.py` | `AnomalyDetectionService.process_single_reading`, `_evaluate_rule_breach`, `_evaluate_z_score` |
| **IsolationForest ML** | `backend/app/services/anomaly_ml_service.py` | `AnomalyMLService.score_reading`, `train_baseline_model` |
| **Synthetic Simulator** | `backend/app/services/synthetic_simulator.py`| `SyntheticDataSimulator.run_cycle`, `_worker_loop`, `_generate_block_reading_value` |
| **Priority Engine** | `backend/app/services/priority_engine.py` | `PriorityEngine.get_high_priority_anomaly` |
| **Reporting Engine** | `backend/app/services/reporting.py` | `ReportingService.generate_report`, `_to_csv`, `_to_pdf` |
| **AI Assistant & Gemini** | `backend/app/ai/assistant/service.py` | `AssistantService.process_query`, `_call_gemini_with_tools` |
| **Gemini Domain Tools** | `backend/app/ai/assistant/gemini_tools.py` | `GEMINI_TOOLS_DECLARATIONS`, `execute_tool_call` |
| **Sensor Catalog** | `backend/app/core/sensor_catalog.py` | `MASTER_SENSOR_CATALOG`, `get_recommended_sensors_for_type` |
| **Database Schema** | `backend/app/db/models.py` | `Organisation`, `User`, `SensorReading`, `AnomalyRecord`, `AIRecommendation`, `IoTDevice` |
| **Frontend Header & Menu**| `frontend/src/components/layout/Header.tsx` | `Header`, `#dashboard-more-menu-dropdown`, `handleLogout` |
| **Dashboard Style System** | `frontend/src/lib/dashboardStyles.ts` | `DASHBOARD_STYLES`, `resolveSections`, `getStyleDefinition` |
| **Theme & Color Engine** | `frontend/src/context/ThemeContext.tsx` | `ThemeProvider`, `COLOR_THEMES`, `applyThemeToDOM`, `applyColorThemeToDOM` |
| **Demo Mode Context** | `frontend/src/context/DemoContext.tsx` | `DemoProvider`, `changeSimulatedDay`, `toggleDemoMode`, `simElapsedSeconds` |
| **Notification Engine** | `frontend/src/context/NotificationContext.tsx`| `NotificationProvider`, `refreshNotifications`, `markAsRead` |
| **AI Assistant UI** | `frontend/src/components/ai/GreenNexaAssistant.tsx`| `GreenNexaAssistant`, `handleSendMessage`, `toggleListening`, `speakText` |

---
*End of Master System Map — GreenNexa Sustainability & Resource Governance Platform.*
