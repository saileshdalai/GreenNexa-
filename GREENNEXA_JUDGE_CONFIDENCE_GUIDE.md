# GreenNexa — Developer & Judge Confidence Guide
## The Complete Internal Engineering & Project Presentation Handbook

> **Audience**: Personal study, developer mastery, and hackathon / investor / academic judge defence.  
> **Source Base**: 100% verified against the actual GreenNexa codebase (`frontend/`, `backend/`, database models, services, ML pipelines, and test suites).  
> **Security Protocol**: Strict zero-secret-disclosure applied (`[REDACTED]` for any internal keys or hashes).  
> **Philosophy**: Real Code > Assumptions | Verified Behaviour > Buzzwords.

---

## Table of Contents

1. [The Actual GreenNexa Tech Stack](#1-the-actual-greennexa-tech-stack)
2. [Frontend — Explained for Beginners](#2-frontend--explained-for-beginners)
3. [Every Major Frontend Control — What Does It Actually Do?](#3-every-major-frontend-control--what-does-it-actually-do)
4. [Backend — Explained for Beginners](#4-backend--explained-for-beginners)
5. [Frontend ➔ Backend Communication (Step-by-Step Traces)](#5-frontend--backend-communication-step-by-step-traces)
6. [Database Architecture — Simple & Accurate](#6-database-architecture--simple--accurate)
7. [Authentication & Security — Judge Explanation](#7-authentication--security--judge-explanation)
8. [Demo Mode & Autonomous Simulator](#8-demo-mode--autonomous-simulator)
9. [Real IoT Data vs Synthetic Telemetry](#9-real-iot-data-vs-synthetic-telemetry)
10. [AI & Machine Learning Engine (How It Actually Works)](#10-ai--machine-learning-engine-how-it-actually-works)
11. [Forecasting Engine Deep Dive](#11-forecasting-engine-deep-dive)
12. [Anomaly Detection Pipeline](#12-anomaly-detection-pipeline)
13. [Prescriptive Recommendation Engine](#13-prescriptive-recommendation-engine)
14. [Gemini Multilingual AI Assistant](#14-gemini-multilingual-ai-assistant)
15. [What-If Predictive Scenario Simulator](#15-what-if-predictive-scenario-simulator)
16. [Municipality System vs Standard Facilities](#16-municipality-system-vs-standard-facilities)
17. [Roles, Permissions & Tenant Isolation](#17-roles-permissions--tenant-isolation)
18. [The Complete End-to-End System Story](#18-the-complete-end-to-end-system-story)
19. [Concrete Walkthrough: "Abnormal Water Consumption Surge"](#19-concrete-walkthrough-abnormal-water-consumption-surge)
20. [Architectural Rationale ("Why Did We Choose This Tech?")](#20-architectural-rationale-why-did-we-choose-this-tech)
21. [Judge-Ready Speaking Notes (24 Core Answers)](#21-judge-ready-speaking-notes-24-core-answers)
22. [Top 30+ Judge Cross-Questions & One-Line Memorization Answers](#22-top-30-judge-cross-questions--one-line-memorization-answers)
23. ["Don't Say This" — Traps to Avoid & Honest Technical Alternatives](#23-dont-say-this--traps-to-avoid--honest-technical-alternatives)
24. [Technical Glossary You Must Know](#24-technical-glossary-you-must-know)
25. [The 5-Minute Quick Revision Sheet](#25-the-5-minute-quick-revision-sheet)
26. [Code Traceability Index](#26-code-traceability-index)

---

## 1. The Actual GreenNexa Tech Stack

| Layer | Actual Technology | Primary Purpose | Where Used in Code |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | **Next.js 14** (App Router) | Server-side rendering, client hydration, route handling | `frontend/src/app/` |
| **Frontend Language** | **TypeScript / React 18** | Type-safe UI components, client-side hooks, state management | `frontend/src/` |
| **Styling & Design** | **Vanilla CSS Modules** | Custom design system, CSS variables for dynamic Day/Night & 6 color themes | `frontend/src/app/globals.css`, `Header.module.css` |
| **Iconography** | **Lucide React** | Lightweight SVG UI icons | Throughout `frontend/src/components/` |
| **Frontend State** | **React Context API** | Global application state (Auth, Theme, Styles, Demo, Notifications) | `frontend/src/context/` (6 distinct contexts) |
| **API Client** | **Fetch API Wrapper (`api.ts`)**| Centralized HTTP client with automatic JWT token attachment | `frontend/src/lib/api.ts` |
| **Backend Framework** | **FastAPI** (Python 3.11+) | High-performance asynchronous REST API, automatic OpenAPI docs | `backend/app/main.py` |
| **Data Validation** | **Pydantic v2** | Strict request/response schema parsing and type validation | `backend/app/schemas/` |
| **Database Engine** | **SQLite** (file-based) | Primary zero-setup relational database (`greennexa_test.db`) | Project root / `backend/app/db/database.py` |
| **Database ORM** | **SQLAlchemy 2.0** | Object-relational mapping, database transactions, table models | `backend/app/db/models.py` |
| **Password Security** | **Passlib (PBKDF2 SHA-256)** | Salted, cryptographic password hashing (zero plaintext storage) | `backend/app/core/security.py` |
| **Token Security** | **PyJWT (HS256)** | Stateless bearer token creation and cryptographic signature checking | `backend/app/core/security.py` |
| **Simulation Engine** | **Python `threading` & `asyncio`** | Autonomous 30-second multi-tenant sensor data generation | `backend/app/services/synthetic_simulator.py` |
| **Time-Series Forecasting**| **Statsmodels** | Holt-Winters Exponential Smoothing with 24-hour diurnal seasonality | `backend/app/services/forecasting.py` |
| **Unsupervised Outlier ML**| **Scikit-Learn (`IsolationForest`)**| Multidimensional anomaly scoring across 8-feature vectors | `backend/app/services/anomaly_ml_service.py` |
| **Statistical Detection**| **NumPy & Pandas** | Rolling 24-hour baseline rolling means and 3-sigma Z-score testing | `backend/app/services/anomaly_detection.py` |
| **Conversational AI** | **Google GenAI SDK (`gemini-2.5-flash`)**| Multi-turn LLM chat with server-side tool calling (15 tools) | `backend/app/ai/assistant/service.py` |
| **Speech Processing** | **Web Speech API** | Browser-native SpeechRecognition (Voice In) & SpeechSynthesis (Voice Out) | `frontend/src/components/ai/GreenNexaAssistant.tsx` |
| **PDF Reporting** | **ReportLab** | Server-side compilation of formatted PDF audit reports | `backend/app/services/reporting.py` |
| **Automated Testing** | **Pytest** | 48 automated test suites verifying regressions, auth, ML, and APIs | `backend/tests/` |

---

## 2. Frontend — Explained for Beginners

### What does "Frontend" mean in GreenNexa?
The frontend is the visual website that runs inside the user's browser. It is what facility operators, school principals, hospital engineers, and municipal commissioners see and interact with on their laptops, tablets, or phones.

### Which framework is used?
We use **Next.js 14** with the modern **App Router** (`frontend/src/app`). Inside Next.js, every page and button is built using **React 18** and **TypeScript**.

### Folder Structure (The Big Picture)
```
frontend/src/
 ├── app/             ──> The actual web pages and URL routes (e.g. /login, /dashboard)
 ├── components/      ──> Reusable building blocks (Buttons, Header, Sidebar, Modals, Assistant)
 ├── context/         ──> Global memory providers (Keeps track of logged-in user, active theme, etc.)
 ├── lib/             ──> Helper scripts (API client, style definitions, organization helpers)
 └── types/           ──> TypeScript definitions (Shapes of User, Organisation, Reading, Anomaly)
```

### Important Pages You Must Know
1. **`/login`** (`frontend/src/app/login/page.tsx`): The entry gate. Has a mandatory **Government vs Private** selector so users only log into their intended facility ownership scope.
2. **`/dashboard`** (`frontend/src/app/dashboard/page.tsx`): The main operational screen. Renders one of 4 presentation styles (Executive, Operations, Analytics, Command Center).
3. **`/dashboard/modules/[module]`** (`frontend/src/app/dashboard/modules/...`): Detailed deep-dive screens for each of the 8 core modules (Energy, Water, Waste, etc.).
4. **`/forecast`** (`frontend/src/app/forecast/page.tsx`): Interactive predictive charts showing where energy or water usage is heading over 24h, 7d, 15d, and 30d.
5. **`/anomalies`** (`frontend/src/app/anomalies/page.tsx`): The alert desk where operators can see, acknowledge, and resolve active threshold or ML breaches.
6. **`/recommendations`** (`frontend/src/app/recommendations/page.tsx`): AI-suggested operational changes with estimated kilowatt-hour or rupee savings.
7. **`/reports`** (`frontend/src/app/reports/page.tsx`): Clean report builder to export CSV data or download official PDF summaries.
8. **`/settings`** (`frontend/src/app/settings/page.tsx`): Where tenant admins can toggle sensors, edit baselines, or clear operational test data.
9. **`/super-admin/*`** (`frontend/src/app/super-admin/...`): Dedicated platform portal for platform owners to register new organisations, manage storage, and reset passwords.

### Important Contexts (Global Memory)
A "Context" in React is like a shared global whiteboard that any page can read without passing data down through 50 layers of components:
- **`AuthContext`**: Remembers who is logged in, their JWT token, their role (`SUPER_ADMIN` or `ADMIN`), and which organization is currently being viewed.
- **`DemoContext`**: Coordinates the simulated calendar date (e.g. `20 Sep 2026`), Demo Mode state, and the ticking 30-second simulation cycle timer.
- **`DashboardStyleContext`**: Remembers which of the 4 visual layouts the user prefers (`EXECUTIVE`, `OPERATIONS`, `ANALYTICS`, `COMMAND_CENTER`).
- **`ThemeContext`**: Stores Day/Night mode and the 6 color choices (`emerald`, `ocean-blue`, `indigo`, `teal`, `graphite`, `amber`).
- **`NotificationContext`**: Polls the backend every 15 seconds to check if any new anomalies were detected, turning on glowing red alert dots on menu items.

---

## 3. Every Major Frontend Control — What Does It Actually Do?

When you click something on the screen, what happens under the hood? Here is the exact breakdown:

| Control / Button | Where It Lives | What the User Sees | What the System Actually Does Internally |
| :--- | :--- | :--- | :--- |
| **Government / Private Selector** | Login Page | Two toggle buttons: "Government" or "Private" | Tells the backend auth endpoint which ownership type to check. If an admin chooses Private but their account belongs to a Government hospital, login is rejected. |
| **Login Button** | Login Page | "Sign In" button with loading spinner | Calls `POST /api/v1/auth/login`. If valid, receives a JWT token, stores it in browser `localStorage`, and redirects to `/dashboard` or `/super-admin`. |
| **⋯ ("More") Menu** | Top Right Header | A round button with three dots (`⋯`) | Opens a dropdown containing style pickers, color themes, municipal tools, Demo Mode, Change Day, and session controls. |
| **Dashboard Style** | Inside ⋯ Menu | Submenu with 4 choices: Executive, Operations, Analytics, Command Center | Changes the layout and card priority in `DashboardStyleContext`. Saves the choice in browser `localStorage`. Does NOT alter any backend data. |
| **Theme / Colour** | Inside ⋯ Menu | 6 color swatches (Emerald, Ocean Blue, Indigo, Teal, Graphite, Amber) | Injects `data-color-theme` into the HTML `<body>`. All CSS variables change instantly to match that color. |
| **Day / Night Toggle** | Inside ⋯ Menu | Sun ☀️ / Moon 🌙 button | Toggles `data-theme="day"` (clean white surfaces) or `data-theme="night"` (obsidian dark surfaces). |
| **Add ➔ Ward / Org** | Inside ⋯ Menu | "Add" option with sub-buttons "Ward" and "Organisation" | **Only visible for Municipalities**. Clicking "Ward" opens `AddWardModal` (`POST /wards`). Clicking "Organisation" opens `AddGovernmentOrgModal` to associate another public hospital or college. |
| **Change Day** | Inside ⋯ Menu | "Change Day" button | Calls `POST /api/v1/simulator/synthetic/change-day`. Advances the database simulation calendar by +1 day. Daily meters reset for the new morning. |
| **Demo Mode ON/OFF** | Inside ⋯ Menu | Toggle pill showing "ON" or "OFF" | Calls `POST /api/v1/simulator/synthetic/start` with `{ demo_mode: true }`. Tells the backend simulator to inject one realistic anomaly every 30 seconds for testing. |
| **Notifications** | Inside ⋯ Menu & Sidebar | Bell icon with unread count badge & red dot | Clicking navigates to `/messages`. Tells `NotificationContext` which alarms the user has now viewed. |
| **Logout** | Inside ⋯ Menu | Red "Logout" button | Calls backend `/auth/logout`, tells the simulator to stop generating data for this org, deletes tokens from `localStorage`, and returns to home. |
| **AI Assistant Launcher** | Bottom Right Floating | Floating circular button with GreenNexa bot icon | Opens the chat window. Connects to `POST /api/v1/ai/chat` with voice input and text-to-speech support. |
| **Acknowledge Anomaly** | Anomalies Page | "Acknowledge" button on an anomaly row | Calls `PATCH /api/v1/anomaly/{id}/acknowledge`. Updates database status from `OPEN` to `ACKNOWLEDGED`. Operator takes ownership. |
| **Resolve Anomaly** | Anomalies Page | "Resolve" button on an anomaly row | Calls `PATCH /api/v1/anomaly/{id}/resolve`. Moves status to `RESOLVED`. Removes it from the active alarm queue. |
| **Manage Storage** | Inside ⋯ Menu | "Manage Storage" button (**Super Admin Only**) | Links to `/super-admin/storage`. Displays the real physical `.db` file size on the disk and breaks down logical data usage per organization. |
| **Clear Data (Tenant)**| Settings Page | Red "Clear Data" button | Calls `POST /api/v1/organisations/{id}/clear-data`. Deletes test sensor readings, anomalies, and AI recommendations for this organization, but preserves the admin and blocks. Runs SQLite `VACUUM`. |
| **Clear All Data** | Super Admin Settings | Big red "Clear All Platform Data" button | Requires entering the secret confirmation password AND typing `"CLEAR ALL DATA"`. Deletes every organization and reading on the platform, leaving only the primary Super Admin. Runs SQLite `VACUUM`. |

---

## 4. Backend — Explained for Beginners

### What does "Backend" mean in GreenNexa?
The backend is the engine running on the server. The user never sees it directly. It handles security, verifies passwords, checks who is allowed to view what, runs the background simulation, performs the AI and machine learning calculations, and talks directly to the database.

### Which framework is used?
We use **FastAPI**, written in **Python 3.11+**. FastAPI was chosen because it is blazing fast, natively supports asynchronous operations (`async/await`), and works seamlessly with Python's top data science and ML libraries (NumPy, Pandas, Scikit-Learn, Statsmodels, and Google GenAI).

### Backend Folder Structure
```
backend/app/
 ├── api/v1/          ──> All API route files (Where HTTP endpoints live)
 ├── core/            ──> Security, token rules, sensor catalogs, spatial grouping rules
 ├── db/              ──> Database connections, SQLAlchemy models, database seeders
 ├── schemas/         ──> Pydantic models (Validates incoming and outgoing JSON data)
 ├── services/        ──> Heavy business logic (Simulator, ML, Forecasting, Anomaly Detector, Reports)
 └── ai/assistant/    ──> Gemini integration, multilingual NLU parser, and domain tools
```

### The Life of an API Request (FastAPI Middleware & Dependencies)
Every time a request arrives at the backend:
1. **CORS Middleware**: Checks if the web browser is allowed to talk to the backend (`main.py`).
2. **Dependency `get_db`**: Opens a clean, dedicated database session and closes it automatically when finished (`database.py`).
3. **Dependency `get_current_user`**: Inspects the `Authorization: Bearer <token>` header, decodes the JWT, verifies the cryptographic signature, and loads the active user from the database (`dependencies.py`).
4. **Dependency `require_roles(...)`**: Checks if the user is a `SUPER_ADMIN` or `ADMIN`. If an ordinary admin tries to call a Super Admin endpoint, FastAPI immediately returns `403 Forbidden` (`dependencies.py`).
5. **Tenant Isolation Check `verify_organisation_access(...)`**: Ensures an Admin from Organization A cannot view or touch data belonging to Organization B (`dependencies.py`).

---

## 5. Frontend ➔ Backend Communication (Step-by-Step Traces)

Here is how the frontend and backend talk to each other in 6 real scenarios.

### Scenario 1: User Logs In
```
[User clicks "Sign In"]
  │
  ▼
Frontend: login/page.tsx calls AuthContext.login(email, password, orgType)
  │
  ▼
HTTP Request: POST /api/v1/auth/login
Body: { "email": "admin@hospital.org", "password": "...", "organisation_type": "GOVERNMENT" }
  │
  ▼
Backend: api/v1/auth.py receives request
  ├── Validates schema using Pydantic (LoginRequest)
  ├── Queries DB: User.email == "admin@hospital.org"
  ├── Checks user.is_active == True
  ├── Checks user.organisation.ownership_type == "GOVERNMENT" (Match!)
  ├── Verifies password hash using passlib PBKDF2
  └── Creates JWT access token containing { sub: user.id, role: user.role, org_id: ... }
  │
  ▼
HTTP Response: 200 OK with { "access_token": "eyJhbG...", "token_type": "bearer", "user": {...} }
  │
  ▼
Frontend: AuthContext stores token in localStorage, updates React state, redirects to /dashboard
```

### Scenario 2: Dashboard Loads Live Data
```
[User lands on /dashboard]
  │
  ▼
Frontend: Dashboard page triggers useEffect -> calls api.get("/api/v1/dashboard/kpis")
  │
  ▼
HTTP Request: GET /api/v1/dashboard/kpis
Header: Authorization: Bearer eyJhbG...
  │
  ▼
Backend: api/v1/dashboard.py
  ├── get_current_user decodes token -> extracts active organisation_id
  ├── Queries sensor_readings for today's date WHERE organisation_id = org_id
  ├── Computes current values, baseline comparisons, and today's delta
  ├── Queries anomaly_records for count of active OPEN anomalies
  └── Queries ai_recommendations for latest high-impact suggestions
  │
  ▼
HTTP Response: 200 OK with structured KPI metrics and module summaries
  │
  ▼
Frontend: DashboardStyleContext resolves the selected style and renders the KPI cards
```

### Scenario 3: Real IoT Device Streams Reading
```
[Physical ESP32 micro-controller reads a water pulse meter]
  │
  ▼
HTTP Request: POST /api/v1/iot/sensor-data
Headers:
  X-Device-ID: ESP32-WATER-WING-A
  X-API-Key: [REDACTED_DEVICE_KEY]
Body: {
  "device_id": "ESP32-WATER-WING-A",
  "readings": [{ "sensor_type": "water", "value": 542.5, "unit": "L" }]
}
  │
  ▼
Backend: api/v1/iot.py (_authenticate_iot_device)
  ├── Looks up device in iot_devices table by device_id
  ├── Verifies X-API-Key against device.api_key_hash using PBKDF2
  ├── Verifies device.is_active == True and org.is_active == True
  ├── Verifies organisation_sensor_configs.data_source == "iot"
  ├── Ensures header device_id matches body device_id (spoof guard)
  ├── Inserts new row into sensor_readings table (source='iot')
  ├── Updates device.last_seen_at = now
  └── Calls anomaly_detection_service.process_single_reading() synchronously
  │
  ▼
HTTP Response: 201 Created with { "status": "success", "ingested_count": 1 }
```

### Scenario 4: User Asks AI Assistant a Question
```
[User speaks: "Which block has the highest water consumption?"]
  │
  ▼
Frontend: GreenNexaAssistant.tsx captures speech -> sets inputQuery -> calls api.post("/api/v1/ai/chat")
  │
  ▼
HTTP Request: POST /api/v1/ai/chat
Body: {
  "message": "Which block has the highest water consumption?",
  "session_history": [...],
  "conversation_language": "english"
}
  │
  ▼
Backend: ai/assistant/service.py
  ├── NLU parser detects intent: GET_BLOCK_COMPARISON, metric: "water"
  ├── Assistant sends prompt and available tools to Gemini 2.5 Flash
  ├── Gemini inspects declarations and calls tool: get_block_comparison(metric="water")
  ├── Backend executes get_block_comparison against local SQLAlchemy database
  ├── Tool returns actual database numbers: {"Emergency": "620L", "ICU": "410L", "OPD": "210L"}
  ├── Gemini synthesizes natural language reply explaining Emergency block is highest
  └── Assistant formats suggested follow-up questions
  │
  ▼
HTTP Response: 200 OK with { "reply": "Based on current telemetry, the Emergency Wing...", "data_source": "Database Query" }
  │
  ▼
Frontend: Displays assistant message bubble and speaks the answer aloud using SpeechSynthesis
```

---

## 6. Database Architecture — Simple & Accurate

### What database is used and why?
GreenNexa uses **SQLite** through **SQLAlchemy ORM**.  
*Why SQLite?* Because it requires zero external database servers to install, runs entirely from a single file (`greennexa_test.db`), is extremely fast for read operations, and makes the project 100% portable for demonstrations, offline evaluations, and developer workstations.  
*(Note: Because we use SQLAlchemy models, switching to PostgreSQL in enterprise production requires changing only one line in the `.env` configuration file).*

### The 13 Database Tables

| Table / Model | What It Stores | Relationships & Foreign Keys |
| :--- | :--- | :--- |
| **`organisations`** | Every tenant facility or city municipality (Name, ownership, type, city, address) | 1-to-many with Users, Blocks, Wards, Readings, Devices |
| **`users`** | Administrator and user credentials (Email, hashed password, phone, role) | Belongs to `organisation_id` (null for Super Admin) |
| **`facility_blocks`** | Indoor physical wings/buildings (e.g. "ICU Wing", "Block B", "Hostel 1") | Belongs to `organisation_id` |
| **`municipality_wards`** | Outdoor civic zones for city councils (Ward Number, Ward Name, Population, Area) | Belongs to `municipality_id` (which is an Organisation) |
| **`organisation_sensor_configs`**| Data source mode (`synthetic` or `iot`), enabled sensors, baselines, and simulated date | 1-to-1 with `organisations` |
| **`sensor_readings`** | Time-series telemetry (Timestamp, sensor type, value, unit, is_anomaly, block/ward) | Belongs to `organisation_id`, optional `block_id` or `ward_id` |
| **`anomaly_records`** | Detected incidents (Metric, value, expected range, severity, status, anomaly score) | Belongs to `organisation_id`, optional `block_id` |
| **`ai_recommendations`** | Prescriptive remediation plans (Summary, root causes, actions, estimated savings) | Linked to an `anomaly_id`, belongs to `organisation_id` |
| **`iot_devices`** | Registered hardware devices (Device ID, salted API key hash, model, last seen) | Belongs to `organisation_id` |
| **`messages`** | Internal notification threads, operator alerts, and broadcast logs | Belongs to `organisation_id` |
| **`event_read_states`** | Tracks which user has seen which anomaly (drives the glowing red alert dots) | Maps `user_id` to `anomaly_id` |
| **`password_reset_otps`** | Hashed 6-digit SMS recovery codes, attempt counts, and expiration times | Linked to the user's phone number |
| **`platform_state`** | Global system flags (e.g. `platform_data_cleared` flag to stop auto-reseeding) | Standalone system flag table |

---

## 7. Authentication & Security — Judge Explanation

### Why Frontend-Only Authentication is NOT Enough
If a website only hides buttons using JavaScript, any tech-savvy user can open their browser's Developer Tools and call the backend API directly.  
GreenNexa implements **True Server-Side RBAC**: Even if someone creates a fake button in the frontend, the FastAPI backend inspects the cryptographic JWT signature and rejects unauthorized calls with an `HTTP 401 Unauthorized` or `HTTP 403 Forbidden`.

### The 2 Roles
1. **`SUPER_ADMIN`**: The platform owner. Can view all facilities, create new customer organizations, manage storage, reset any user's password, and wipe test data across the platform.
2. **`ADMIN`**: The facility manager or municipal officer. Strictly restricted to their own organization. They cannot see or modify other schools, hospitals, or cities.

### Government vs Private Ownership Barrier
At login, users must declare whether they are accessing a **Government** or **Private** facility. The backend checks `user.organisation.ownership_type`. If an administrator of a Government Hospital selects "Private", the backend rejects the login with `401 Unauthorized`. This prevents accidental credential usage across different legal sectors.

---

## 8. Demo Mode & Autonomous Simulator

### What is Demo Mode?
Demo Mode is an intelligent background simulator built into the backend (`backend/app/services/synthetic_simulator.py`). It enables evaluators and judges to experience realistic, live facility monitoring without needing hundreds of physical IoT devices wired to the building.

### How It Works Internally
```
[Demo Mode Activated]
        │
        ▼
Simulator Background Thread ticks every 30 seconds (monotonic clock)
        │
        ▼
Checks which organizations are enrolled in Demo Mode
(Strict Scope: Unenrolled organizations remain completely frozen)
        │
        ▼
Generates realistic telemetry for enabled sensors:
- Cumulative Metrics (Energy, Water): Steps forward along a diurnal curve
- Bounded Percentages (Waste): Varies between 15% and 85% bin fill
- Variable Metrics (AQI, Temp): Fluctuates around the configured baseline
        │
        ▼
Injects EXACTLY ONE scenario anomaly per 30-second cycle:
Rotates round-robin through 9 realistic emergency scenarios:
(Water Pipe Leak, Waste Overflow, Rainfall Surge, Drainage Backup, Traffic Jam, etc.)
        │
        ▼
Writes new row to `sensor_readings` table with is_anomaly = True
        │
        ▼
Triggers Anomaly Pipeline:
- Writes `anomaly_records` (Status: OPEN)
- Generates linked `ai_recommendations` with estimated rupee/kWh savings
- Notifies Priority Engine and illuminates the red alert dot in the frontend
```

### Key Technical Guarantees
- **No Backlog Bursts**: If a cycle takes slightly longer, the simulator skips missed ticks rather than firing a flood of catch-up cycles.
- **Module Scoped**: If Demo Mode is toggled while viewing the Energy module, it only simulates energy anomalies, leaving other modules unaffected.
- **Persistent Across Navigation**: The 30-second timer persists across route changes in the frontend using `DemoContext`.

---

## 9. Real IoT Data vs Synthetic Telemetry

GreenNexa supports both simulated environments and physical hardware out of the box:

```
        SYNTHETIC DATA PATH                             REAL HARDWARE IOT PATH
 (Internal Background Simulator)                      (Physical ESP32 / Arduino)
                │                                                 │
                ▼                                                 ▼
    SyntheticDataSimulator Worker                         HTTP POST /api/v1/iot/sensor-data
                │                                                 │
   Generates realistic diurnal values             Authenticated via X-Device-ID & X-API-Key
                │                                                 │
    source = 'synthetic'                              source = 'iot'
                │                                                 │
                └────────────────────────┬────────────────────────┘
                                         ▼
                         Written to sensor_readings table
                                         │
                                         ▼
                         Evaluated by Anomaly & ML Engine
                                         │
                                         ▼
                         Rendered on Unified UI Dashboard
```

### The Difference in One Sentence
- **Synthetic Data**: Generated mathematically inside the backend server to simulate 24-hour facility patterns for offline testing.
- **Real IoT Data**: Sent over the network by real microcontrollers using secret API keys and physical sensors, subject to real-world network connectivity.

---

## 10. AI & Machine Learning Engine (How It Actually Works)

GreenNexa does not rely on simple static "if value > 100" checks. It uses a **Tri-Layer Detection & Predictive Machine Learning Architecture**:

```
                       NEW SENSOR READING ARRIVES
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
      LAYER 1                   LAYER 2                   LAYER 3
  Threshold Rules         Statistical Z-Score        IsolationForest ML
(Super Admin Limits)     (Rolling Standard Dev)   (8-Dimensional Vector)
         │                         │                         │
   Checks if value           Evaluates:                 Extracts 8 features:
   exceeds baseline          Z = (x - μ) / σ            Rate of change, hour,
   by Warning (+15%)                                    rolling 1h avg, baseline
   or Critical (+30%)        Flags if |Z| >= 3.0        deviation, etc.
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   ▼
                       Unified Arbiter Engine
                  Assigns Severity: CRITICAL or HIGH
                  Writes AnomalyRecord & AIRecommendation
```

### The 3 Layers Explained Simply
1. **Layer 1: Rule-Based Threshold Engine**: Compares the incoming reading against the organization's custom baseline. If baseline is 100 kWh and warning threshold is 15%, any reading over 115 kWh triggers a warning.
2. **Layer 2: Statistical 3-Sigma Z-Score**: Computes the mean ($\mu$) and standard deviation ($\sigma$) over the last 24 hours of data. If a reading spikes by more than 3 standard deviations ($|Z| \ge 3.0$), it is mathematically classified as an abnormal surge.
3. **Layer 3: Unsupervised Machine Learning (`IsolationForest`)**: Uses Scikit-Learn's `IsolationForest` algorithm on an 8-dimensional feature vector (value, 1-hour average, 24-hour average, rate of change, hour of day, day of week, baseline difference, percentage delta). It isolates multidimensional outliers that simple thresholds miss (e.g. high energy usage at 3:00 AM on Sunday when the building is supposed to be empty).

---

## 11. Forecasting Engine Deep Dive

### How Does Forecasting Work?
- **Algorithm**: Statsmodels `ExponentialSmoothing` implementing **Holt-Winters Seasonal Smoothing**.
- **Diurnal Seasonality**: The model explicitly accounts for 24-hour daily human cycles (usage rises in the morning, peaks in the afternoon, and drops at night).
- **Graceful Fallbacks**:
  - If 24+ historical readings exist $\rightarrow$ Fits full Holt-Winters additive diurnal model.
  - If fewer readings exist $\rightarrow$ Falls back to linear trend Holt smoothing.
  - If fewer than 3 readings exist $\rightarrow$ Returns mean baseline with an explicit notice: *"Insufficient data history for full seasonal forecast."*
- **Dynamic 95% Confidence Intervals**: For every future hour, the engine computes an uncertainty band ($\hat{y} \pm 1.96 \cdot \sigma$) showing operators the range of likely outcomes.
- **Honest Judge Note**: *The forecast is a statistical projection based on past operational patterns, not a guaranteed future promise.*

---

## 12. Anomaly Detection Pipeline

### The 4 Stages of an Anomaly's Life
```
[Detection] ──> OPEN ──> [Operator clicks Acknowledge] ──> ACKNOWLEDGED ──> [Issue Fixed] ──> RESOLVED
                  │
                  └───> [Operator marks False Alarm] ───> DISMISSED
```

1. **`OPEN`**: Anomaly newly detected. Triggers glowing red dots across the sidebar and header.
2. **`ACKNOWLEDGED`**: Operator has clicked "Acknowledge" on the dashboard, taking formal responsibility.
3. **`RESOLVED`**: The maintenance team has physically repaired the leak or equipment. The alert is cleared from active counts.
4. **`DISMISSED`**: Flagged as a known benign event (e.g. scheduled maintenance testing).
- **Crucial Architectural Rule**: GreenNexa **never** auto-resolves anomalies just because the next sensor reading looks normal. Real plumbing leaks or electrical shorts require human verification to resolve.

---

## 13. Prescriptive Recommendation Engine

GreenNexa does not just sound alarms—it tells operators **what to do** to resolve the issue (`backend/app/services/anomaly_detection.py:270-340`).

### Anatomy of an AI Recommendation
When an anomaly occurs, the engine generates an `AIRecommendation` containing:
1. **Summary**: Clear one-line executive description (e.g. *"Inspect high-load equipment in Emergency Wing."*).
2. **Root Causes**: Probable physical reasons separated by bullet points (e.g. *"Compressor valve failure | Chilled water loop leakage | Thermostat miscalibration"*).
3. **Action Steps**: Specific step-by-step guidance for technicians (e.g. *"1. Check refrigerant pressure. 2. Verify damper positions. 3. Reduce non-essential circuit loads."*).
4. **Quantified Savings**: Projects estimated kilowatt-hour or water savings and financial savings in Indian Rupees (₹).

---

## 14. Gemini Multilingual AI Assistant

### How the Gemini Assistant Works Internally
- **Model**: Google's `gemini-2.5-flash` running through the official `google-genai` Python SDK.
- **Zero Frontend Secrets**: The `GEMINI_API_KEY` is stored strictly on the backend server. The user's browser never sees or holds the API key.
- **Multi-Turn Context**: Remembers the last 6 messages of conversation to understand follow-up questions (e.g., *"How does that compare to yesterday?"*).
- **Multilingual Support**: Supports English, Hinglish (*"Aaj ka water leakage kidhar hua?"*), Odia script (*"କେଉଁ ବ୍ଲକରେ ଅଧିକ ପାଣି ବ୍ୟବହାର ହେଉଛି?"*), and Roman Odia (*"ko block re adhika energy usage hauchhi?"*).
- **Server-Side Tool Calling (15 Tools)**:
  Gemini does not guess numbers. It uses function calling to query the actual database:
  - *Tenant Tools*: `get_current_metrics`, `get_active_anomalies`, `get_forecast`, `get_block_comparison`, `get_recommendations`, `get_facility_status`, and 4 What-If scenario tools.
  - *Super Admin Tools*: `get_platform_summary`, `get_organisation_list`, `compare_organisations`.
- **Tenant Isolation**: An Admin from Hospital A cannot ask Gemini to inspect College B. Gemini receives only the authenticated user's organization scope.

---

## 15. What-If Predictive Scenario Simulator

What-If analysis lets facility managers simulate operational decisions before spending money:
- **Energy Scenario**: Simulates what happens if HVAC setpoints are relaxed by 15% or solar panels are installed. Computes expected daily kWh saved, rupee savings, and avoided metric tons of $\text{CO}_2$.
- **Water Scenario**: Simulates installing low-flow aerators across restrooms, projecting daily kilolitres conserved and reservoir supply extension.
- **Waste Scenario**: Simulates a 20% increase in cafeteria composting, estimating landfill diversion and municipal disposal fee reductions.
- **Traffic Scenario**: Simulates staggered corporate office shift timings, projecting peak queue length reductions at main entrance gates.

---

## 16. Municipality System vs Standard Facilities

A **Municipality** in GreenNexa is fundamentally different from a standalone building:

```
        STANDALONE FACILITY                             MUNICIPALITY CORPORATION
       (University, Hospital)                           (City Council / Smart City)
                 │                                                   │
                 ▼                                                   ▼
       Divided into BLOCKS                                  Divided into WARDS
     ("Block A", "ICU Wing")                               ("Ward 01", "Ward 12")
                 │                                                   │
        Indoor Measurements                                  Outdoor Civic Infrastructure
       (HVAC Energy, Plumbing)                           (Streetlights, Sewage, Traffic, Parks)
                 │                                                   │
         Single Institution                                  Regional Oversight
                                                     (Associates External Government Hospitals)
```

### The Government-Only Rule
Municipalities can link other public facilities into their regional dashboard (e.g. Bhubaneswar Municipal Corporation linking Capital Hospital). However, the API strictly enforces `ownership_type == 'GOVERNMENT'`. Commercial private entities cannot be linked to public municipal infrastructure.

---

## 17. Roles, Permissions & Tenant Isolation

| Capability | SUPER_ADMIN | ADMIN | Technical Mechanism |
| :--- | :---: | :---: | :--- |
| **Log into Platform** | Yes | Yes | `api/v1/auth.py` |
| **Switch Between Organizations** | Yes (Any Org) | No (Locked to Own) | Scoped via JWT token claims |
| **Create New Facilities & Admins** | Yes | No | Protected by `require_roles(SUPER_ADMIN)` |
| **Reset User Passwords** | Yes (Needs Confirmation) | No | Protected by confirmation secret password |
| **View Telemetry Dashboard** | Yes | Yes (Own Org) | Database query filtered by `organisation_id` |
| **Configure Sensor Baselines** | Yes | Yes (Own Org) | `organisations/{id}/sensor-config` |
| **Acknowledge / Resolve Alarms** | Yes | Yes (Own Org) | `anomaly/{id}/acknowledge` |
| **Manage Wards & Associated Orgs** | Yes | Yes (Municipality Admin) | Verified via `isMunicipality(org)` |
| **Wipe Entire Platform ("Clear All Data")** | Yes (Double Confirm) | No | `super-admin/clear-all-data` |
| **Manage Physical Storage** | Yes | No | `super-admin/storage` |

---

## 18. The Complete End-to-End System Story

When presenting to a judge, tell this complete, logical story:

1. **Step 1: Onboarding**: A facility is registered on the platform by the Super Admin. The campus type (Hospital, University, etc.) is chosen, blocks are named, and recommended sensors are automatically assigned with standard baseline thresholds.
2. **Step 2: Ingestion**: Telemetry starts entering the system. Either physical IoT hardware streams data over HTTP with device API keys, or the autonomous simulator generates realistic 30-second cycles.
3. **Step 3: Verification & Storage**: Every reading is validated by Pydantic schemas, tagged with its physical block or civic ward, and stored permanently in the database.
4. **Step 4: AI & ML Inspection**: The tri-layer detection engine continuously checks the reading against baseline threshold deltas, rolling statistical Z-scores, and the Scikit-Learn `IsolationForest` outlier model.
5. **Step 5: Incident Creation**: When an abnormal surge occurs, the backend logs an `AnomalyRecord` and automatically generates an `AIRecommendation` detailing root causes and financial savings.
6. **Step 6: Notification**: The notification engine flags the event in `event_read_states`, immediately turning on glowing red alert dots on the operator's sidebar and module menus.
7. **Step 7: Operator Action**: The facility manager reviews the alert on `/anomalies`, acknowledges it, consults the Gemini Assistant for block comparisons, and dispatches technicians to fix the physical fault.
8. **Step 8: Resolution & Reporting**: Once repaired, the operator marks the anomaly `RESOLVED`. They navigate to `/reports` and export an official PDF compliance document for regulatory records.

---

## 19. Concrete Walkthrough: "Abnormal Water Consumption Surge"

If a judge asks: *"Give me one real example of how GreenNexa handles an incident from start to finish"*, use this exact scenario:

- **1. What Happened**: At 2:15 AM, a main distribution pipe fractures in the Emergency Wing of a hospital. Water flow spikes to 850 Litres/hr (normal night baseline is 200 Litres/hr).
- **2. Ingestion**: The pulse flow meter on the pipe streams the reading to the backend.
- **3. Detection**:
  - *Layer 1 (Rules)*: 850L exceeds the 200L baseline by +325% (Critical threshold is +30%).
  - *Layer 2 (Z-Score)*: Statistical Z-Score calculates to $Z = +4.8$ standard deviations above the 24-hour night mean.
  - *Layer 3 (ML)*: `IsolationForest` marks the feature vector as an extreme outlier.
- **4. Incident Created**: Backend logs Anomaly ID `#ANOM-8492` with `severity = CRITICAL` and `status = OPEN`.
- **5. Recommendation Generated**: Linked recommendation is created: *"Possible plumbing rupture in Emergency Wing. Inspect main isolation gate valve. Estimated daily water loss: 15,600 Litres (₹1,248/day)."*
- **6. Notification**: The operator's dashboard lights up with a glowing red dot next to **Modules ➔ Water Supply**.
- **7. Investigation**: The night supervisor opens GreenNexa, sees the critical alert, and asks the AI Assistant: *"Is this happening across the whole hospital or just Emergency?"*
- **8. AI Response**: Gemini executes `get_block_comparison(metric='water')` and answers: *"The surge is isolated entirely to the Emergency Wing. ICU and OPD blocks are operating at normal baselines."*
- **9. Physical Action**: Supervisor shuts off Isolation Valve #3 in the Emergency Wing, stopping the flood.
- **10. Resolution**: Supervisor clicks **Resolve Anomaly** in GreenNexa. The red dot extinguishes, the priority alarm clears, and the incident is archived in the audit log.

---

## 20. Architectural Rationale ("Why Did We Choose This Tech?")

| Technology | What It Does in GreenNexa | Practical Architectural Reason Based on Implementation |
| :--- | :--- | :--- |
| **Next.js 14 & React 18** | Client-side dashboard & UI routing | Provides fast client-side transitions, component modularity, and easy integration with modern visualization libraries. |
| **Vanilla CSS Architecture** | Dynamic styling and themes | Direct control over CSS variables (`--clr-primary`) makes switching between Day/Night and 6 color palettes instant with zero CSS bundle bloat. |
| **FastAPI (Python)** | REST API backend gateway | Blazing-fast async request handling combined with immediate, native access to Python's data science ecosystem (Scikit-Learn, Statsmodels, GenAI). |
| **SQLite with SQLAlchemy** | Relational data persistence | Zero-configuration local database that runs out of a single file (`greennexa_test.db`), making development, evaluation, and hackathon presentation completely frictionless. |
| **PBKDF2 Password Hashing** | Cryptographic user credential storage | Industry-standard salted cryptographic hashing prevents credential leaks even if the database file is directly inspected. |
| **Statsmodels Holt-Winters** | Time-series load forecasting | Specifically designed for recurring diurnal (24-hour) human behavioral cycles, providing accurate seasonal curves without requiring massive deep-learning GPU infrastructure. |
| **Scikit-Learn IsolationForest**| Unsupervised outlier anomaly detection | Detects complex multi-variable anomalies without needing pre-labeled training datasets, making it adaptable to any new facility. |
| **Gemini 2.5 Flash** | Conversational AI reasoning | Fast inference speeds, native support for server-side function/tool calling, and multilingual fluency across regional Indian languages. |
| **ReportLab** | PDF document compilation | Programmatically compiles clean, publication-grade PDF documents directly on the server without needing headless browser dependencies. |

---

## 21. Judge-Ready Speaking Notes (24 Core Answers)

### 1. What is GreenNexa?
> "GreenNexa is an enterprise sustainability and facility intelligence platform. It ingests IoT telemetry across 8 core modules—like energy, water, and waste—detects anomalies using machine learning, forecasts future consumption, and gives operators an interactive multilingual AI assistant to take immediate action."

### 2. What problem does it solve?
> "Most facility managers manage resources in silos using manual logbooks or fragmented meters. By the time a water leak or an electrical overload is noticed, thousands of litres of water or kilowatt-hours have been wasted. GreenNexa unifies all facility operations into one dashboard with real-time anomaly detection and predictive guidance."

### 3. What is the high-level architecture?
> "GreenNexa uses a decoupled architecture. The frontend is built with Next.js 14 and React. The backend is a high-performance Python FastAPI service. Data is stored in a relational database via SQLAlchemy, analyzed through an anomaly and forecasting ML pipeline, and interfaced through a multilingual Gemini assistant."

### 4. What did you use in the frontend?
> "We used Next.js 14 with TypeScript, React 18, and Vanilla CSS with CSS custom properties. We built a custom design system supporting Day and Night modes and 6 color palettes, managed through 6 centralized React Contexts."

### 5. What did you use in the backend?
> "We used Python 3.11 with FastAPI. We use Pydantic v2 for request validation, passlib PBKDF2 for password hashing, and PyJWT for stateless session security."

### 6. What database did you use?
> "We use SQLite managed via SQLAlchemy 2.0. It contains 13 normalized tables covering organizations, users, physical blocks, civic wards, sensor readings, anomalies, recommendations, and IoT devices."

### 7. How does data flow through the system?
> "Data enters either from physical IoT hardware via our authenticated API or from our autonomous 30-second simulation engine. It is validated, written to the database, evaluated by our tri-layer anomaly detector, and immediately updated on the dashboard."

### 8. How does AI/ML work in GreenNexa?
> "We use machine learning for two primary tasks: First, Holt-Winters exponential smoothing in Statsmodels to forecast multi-day diurnal consumption. Second, an unsupervised IsolationForest model in Scikit-Learn that flags anomalous readings based on an 8-dimensional feature vector."

### 9. How does anomaly detection work?
> "We use a tri-layer pipeline: Layer 1 evaluates custom baseline percentage thresholds. Layer 2 calculates a rolling 24-hour statistical 3-sigma Z-Score. Layer 3 evaluates an unsupervised Isolation Forest model. If an anomaly is verified, an alert is logged and a recommendation is generated."

### 10. How does forecasting work?
> "Our forecasting service uses Statsmodels Exponential Smoothing with 24-hour additive diurnal seasonality. It predicts future hourly consumption over 24-hour, 7-day, 15-day, and 30-day horizons, complete with a dynamic 95% confidence interval."

### 11. How are recommendations generated?
> "When an anomaly occurs, our recommendation service inspects the metric, physical block, and severity. It generates a clear summary, lists probable mechanical root causes, provides step-by-step action items, and calculates estimated rupee and energy savings."

### 12. How does the Gemini AI Assistant work?
> "We use Google's Gemini 2.5 Flash via the official Python SDK. We implemented 15 custom server-side tools. When a user asks a question, Gemini executes the appropriate tool against our live database, synthesizes the facts, and responds in English, Hinglish, Odia, or Roman Odia."

### 13. How does real IoT work in GreenNexa?
> "Hardware devices like an ESP32 send an HTTP POST request to `/api/v1/iot/sensor-data` with their device ID and secret API key in the headers. The backend authenticates the device, validates the reading, saves it to the database, and runs it through our anomaly pipeline."

### 14. What is Demo Mode?
> "Demo Mode is our built-in simulator that generates realistic, non-decreasing diurnal sensor readings every 30 seconds. It rotates through 9 realistic disaster scenarios to demonstrate live anomaly detection and recommendation handling without requiring physical hardware."

### 15. What is Municipality mode?
> "A Municipality in GreenNexa represents an entire city council. Instead of indoor building blocks, it manages outdoor civic wards. It can also associate other public facilities—like public hospitals and universities—into a unified regional oversight dashboard."

### 16. How is security handled?
> "We enforce salted PBKDF2 password hashing, JWT bearer tokens, and server-side role gating. All destructive actions like password resets or database wipes require an additional secret confirmation password."

### 17. How is tenant isolation handled?
> "Every single database query for telemetry, blocks, or alarms strictly filters by `organisation_id`. An administrator from Hospital A cannot view, query, or modify data belonging to University B."

### 18. What happens when a sensor is disabled?
> "When an administrator disables a sensor, it is immediately removed from the simulator and live dashboard calculations. Historical data is preserved permanently for compliance, and incoming IoT readings for that sensor are rejected with a 422 error."

### 19. What happens when historical data is insufficient?
> "Our forecasting engine checks the historical data density. If fewer than 24 hours of data exist, it gracefully falls back to a linear trend or mean baseline and displays an honest notice explaining that more history is needed for a seasonal forecast."

### 20. What are the current limitations?
> "Currently, our local database defaults to SQLite, which serializes write transactions and is best suited for small-to-medium deployments. In addition, our interactive 3D digital twin exists as a visual UI component rather than a live WebGL BIM pipeline."

### 21. What is implemented vs simulated?
> "All APIs, authentication, database storage, Holt-Winters forecasting, Isolation Forest ML, Gemini assistant, and IoT ingestion endpoints are 100% implemented in real code. The sensor data in Demo Mode is simulated using realistic mathematical formulas."

### 22. Why is this architecture scalable?
> "Because our FastAPI backend is completely stateless and uses SQLAlchemy, scaling to enterprise production simply requires pointing the database connection to a distributed PostgreSQL cluster and placing the FastAPI container behind a load balancer."

### 23. What happens if Gemini is unavailable?
> "If the external Gemini API is unreachable or rate-limited, our assistant gracefully falls back to local regex and keyword-based intent parsing, ensuring core metrics and active alarms can still be queried."

### 24. What happens if an IoT device stops transmitting?
> "The backend tracks a `last_seen_at` timestamp on every registered device. In the Super Admin IoT panel, devices that have not communicated within expected intervals are flagged with an inactive status."

---

## 22. Top 30+ Judge Cross-Questions & One-Line Memorization Answers

### Architecture & Backend
1. **Q: Why FastAPI instead of Django or Flask?**  
   *Answer*: FastAPI provides native asynchronous performance, automatic OpenAPI documentation, and fast Pydantic validation, while integrating seamlessly with Python ML libraries.  
   **One-Liner**: *"FastAPI gives us async speed, native Pydantic validation, and direct access to Python ML libraries."*

2. **Q: How do you handle database sessions across concurrent requests?**  
   *Answer*: We use FastAPI's dependency injection system (`get_db`) with SQLAlchemy's `sessionmaker`, yielding a fresh database session per request and closing it in a `finally` block.  
   **One-Liner**: *"We use FastAPI's `get_db` dependency to yield an isolated session per request that closes automatically."*

3. **Q: Is your authentication stateful or stateless?**  
   *Answer*: It is stateless. User identity and permissions are encoded in cryptographically signed JWT tokens passed via HTTP Authorization Bearer headers.  
   **One-Liner**: *"It is stateless, using cryptographically signed JWT bearer tokens."*

### Frontend & UI
4. **Q: Why Next.js instead of plain React with Vite?**  
   *Answer*: Next.js 14 App Router provides robust server-side routing, automated layout management, built-in optimization, and a structured enterprise project layout.  
   **One-Liner**: *"Next.js 14 gives us structured App Router layouts, cleaner routing, and enterprise scalability."*

5. **Q: How does the dashboard switch between the 4 styles without reloading data?**  
   *Answer*: Data fetching is decoupled from presentation. `DashboardStyleContext` simply re-orders and changes the CSS grid density of existing React components.  
   **One-Liner**: *"The data remains the same; `DashboardStyleContext` simply alters component layout priority and grid density."*

6. **Q: How do the glowing red notification dots work across the UI?**  
   *Answer*: `NotificationContext` polls `/api/v1/notifications/unread` every 15s. The backend checks `event_read_states` to find unacknowledged anomalies and flags modules, blocks, and wards.  
   **One-Liner**: *"The frontend polls an unread endpoint that checks database read states and activates red indicator dots."*

### Database & Storage
7. **Q: Why SQLite instead of PostgreSQL?**  
   *Answer*: SQLite allows the entire system to run zero-setup from a single file, making testing, portability, and demonstrations seamless. We use SQLAlchemy ORM, so switching to Postgres requires changing only the database URL.  
   **One-Liner**: *"SQLite provides zero-setup portability for evaluation, and SQLAlchemy allows an instant switch to PostgreSQL."*

8. **Q: What happens to the physical database file when an admin clears data?**  
   *Answer*: We delete the records and immediately execute SQLite's `VACUUM` command via `safe_vacuum_sqlite`, releasing unused pages back to the host operating system.  
   **One-Liner**: *"We delete the rows and execute SQLite's `VACUUM` command to physically shrink the database file."*

9. **Q: How do you calculate organization storage breakdown in a single SQLite file?**  
   *Answer*: We compute a deterministic logical footprint by querying the exact row counts and text byte sizes owned by that organization's ID.  
   **One-Liner**: *"We calculate a deterministic logical footprint based on the exact record counts and text lengths owned by that organization."*

### Machine Learning & AI
10. **Q: Why Holt-Winters instead of an LSTM or Transformer for forecasting?**  
    *Answer*: Facility energy and water usage exhibit strong 24-hour diurnal periodicity. Holt-Winters models seasonal cycles with high mathematical precision, trains in milliseconds on CPU, and requires zero GPU infrastructure.  
    **One-Liner**: *"Holt-Winters models 24-hour diurnal seasonality accurately on CPU without needing heavy GPU infrastructure."*

11. **Q: How does your Isolation Forest model handle unseen data?**  
    *Answer*: It evaluates an 8-dimensional feature vector comparing the reading against rolling averages, rate-of-change, and baselines. Outliers are isolated near the root of the decision trees.  
    **One-Liner**: *"It scores an 8-feature vector against an ensemble of isolation trees to identify multidimensional outliers."*

12. **Q: What happens if an organization has no historical data for forecasting?**  
    *Answer*: The service checks historical point density. If fewer than 3 readings exist, it returns the baseline with an explicit notice stating that more history is required.  
    **One-Liner**: *"It detects low data density, returns the baseline mean, and displays an honest notice requesting more history."*

13. **Q: What is the purpose of the Priority Engine?**  
    *Answer*: It activates only when 3 or more active anomalies exist simultaneously, ranking them by severity, baseline deviation, and critical module weight to highlight the single most urgent issue.  
    **One-Liner**: *"It activates at 3+ concurrent anomalies to score and rank the single most urgent issue, preventing alert fatigue."*

### Gemini & Assistant
14. **Q: How do you prevent Gemini from hallucinating facility numbers?**  
    *Answer*: Gemini is instructed to answer strictly through server-side tool calling. It executes Python database functions and formats only verified database numbers into its reply.  
    **One-Liner**: *"Gemini does not guess numbers; it executes server-side Python tools that query our database directly."*

15. **Q: Is the user's voice recorded and sent to your server?**  
    *Answer*: No. Voice recognition and speech synthesis are handled locally inside the user's browser using the native Web Speech API. Only the transcribed text string is sent to our backend.  
    **One-Liner**: *"Voice recognition happens locally in the browser via Web Speech API; only the text query is sent to the server."*

16. **Q: How do you protect the Gemini API key?**  
    *Answer*: The Gemini API key is loaded into backend server environment variables. It is never sent to the browser or included in frontend client bundles.  
    **One-Liner**: *"The API key is strictly server-side and never exposed to the frontend."*

### IoT & Telemetry
17. **Q: How do physical IoT devices authenticate with GreenNexa?**  
    *Answer*: Devices pass `X-Device-ID` and `X-API-Key` headers in their HTTP POST requests. The backend verifies the key against a salted PBKDF2 hash in the `iot_devices` table.  
    **One-Liner**: *"Devices send headers authenticated against salted PBKDF2 hashes stored in our database."*

18. **Q: Can an IoT device send data if the organization is in synthetic mode?**  
    *Answer*: No. The API checks `organisation_sensor_configs.data_source`. If it is set to `synthetic`, the IoT gateway rejects the request with a `409 Conflict`.  
    **One-Liner**: *"No, the gateway rejects IoT data with a 409 Conflict if the organization is configured in synthetic mode."*

19. **Q: How do you prevent device spoofing?**  
    *Answer*: The backend verifies that the `X-Device-ID` header matches the `device_id` field inside the JSON payload, and that the device belongs to the active organization.  
    **One-Liner**: *"We enforce a strict match between the header device ID, payload device ID, and organization ownership."*

### Municipality & Multi-Tenancy
20. **Q: What is the difference between a Facility Block and a Municipal Ward?**  
    *Answer*: A Facility Block is an indoor physical building partition (like ICU Wing or Block A). A Municipal Ward is an outdoor geographic civic district with a census population and area.  
    **One-Liner**: *"Facility Blocks are indoor physical building wings; Municipal Wards are outdoor geographic civic districts."*

21. **Q: Can a Municipality associate a private commercial factory into its oversight?**  
    *Answer*: No. The association API strictly verifies `target_org.ownership_type == 'GOVERNMENT'`. Commercial private entities are rejected.  
    **One-Liner**: *"No, our API strictly blocks private entities from municipal public infrastructure."*

22. **Q: Can a Municipality Admin change the sensor baselines of an associated hospital?**  
    *Answer*: No. Municipality access to associated facilities is strictly read-only for regional monitoring. Internal configurations remain under that hospital admin's control.  
    **One-Liner**: *"No, municipal oversight is strictly read-only to preserve institutional autonomy."*

### Security & Reliability
23. **Q: What prevents a user from resetting another user's password?**  
    *Answer*: Only a Super Admin can reset administrative passwords, and that endpoint requires entering a mandatory secret confirmation password. Normal users can only reset their own via verified SMS OTP.  
    **One-Liner**: *"Administrative resets require the Super Admin confirmation secret; users can only reset their own via verified SMS OTP."*

24. **Q: What happens if an operator enters the wrong Government/Private selection at login?**  
    *Answer*: The backend verifies the organization's legal ownership type. If there is a mismatch, it returns an `HTTP 401 Unauthorized` error.  
    **One-Liner**: *"The backend checks the organization's legal type and rejects the login on mismatch with a 401 error."*

25. **Q: How do you prevent accidental data deletion?**  
    *Answer*: Destructive operations require a double confirmation: entering the secret confirmation password and typing the exact confirmation phrase `"CLEAR ALL DATA"`.  
    **One-Liner**: *"We require a secret confirmation password plus typing the exact confirmation phrase."*

### Product & Scalability
26. **Q: What makes GreenNexa different from standard BMS (Building Management Systems)?**  
    *Answer*: Traditional BMS systems are static, expensive, proprietary, and isolated. GreenNexa is multi-tenant, integrates machine learning, provides a multilingual conversational assistant, and bridges indoor facilities with outdoor municipal smart cities.  
    **One-Liner**: *"Unlike static BMS, GreenNexa is multi-tenant, uses predictive ML, includes a conversational AI assistant, and connects facilities to smart cities."*

27. **Q: How long does it take to onboard a new hospital or school?**  
    *Answer*: Less than two minutes. The Super Admin creation wizard auto-selects recommended sensors, generates standard baselines, creates the administrator account, and configures physical blocks in a single atomic transaction.  
    **One-Liner**: *"Under two minutes, thanks to our atomic 4-step wizard with automatic sensor preselection."*

28. **Q: Can GreenNexa run completely offline without an internet connection?**  
    *Answer*: Yes. The Next.js frontend, FastAPI backend, SQLite database, simulation engine, and ML models run 100% locally on localhost. Only the external Gemini assistant requires internet access, and it has an offline fallback.  
    **One-Liner**: *"Yes, the entire core platform runs 100% offline; only Gemini requires external connectivity."*

29. **Q: How does the system handle daylight saving time or calendar dates?**  
    *Answer*: All database timestamps are stored in UTC. The simulation calendar operates on an explicit date model (`simulated_date`) that advances cleanly via our Change Day API.  
    **One-Liner**: *"All timestamps are stored in UTC, and simulation dates advance cleanly via a dedicated calendar API."*

30. **Q: How do you ensure high availability if the backend restarts?**  
    *Answer*: The database stores a `platform_state` table. If a platform wipe was executed, the system suppresses automatic re-seeding on restart, ensuring clean state persistence.  
    **One-Liner**: *"We track platform lifecycle flags in the database so system state persists cleanly across restarts."*

---

## 23. "Don't Say This" — Traps to Avoid & Honest Technical Alternatives

| ❌ NEVER SAY THIS TO A JUDGE | WHY IT'S A TRAP | ✅ SAY THIS INSTEAD (HONEST & IMPRESSIVE) |
| :--- | :--- | :--- |
| *"Our AI is 100% accurate and makes no mistakes."* | No statistical or ML model is 100% accurate. Judges will immediately challenge this. | *"We combine statistical Z-scores and Isolation Forest models with dynamic 95% confidence intervals, giving operators clear uncertainty bounds."* |
| *"GreenNexa is completely real-time in every aspect."* | HTTP polling and 30-second simulation intervals are near-real-time, not hard real-time (like a fighter jet). | *"Our telemetry processes in near-real-time, with sub-second API responses and 15-second client polling cycles."* |
| *"Our AI autonomously fixes building problems without humans."* | The system generates recommendations; human technicians must physically repair broken pipes or valves. | *"GreenNexa detects incidents and automates prescriptive guidance, empowering human operators to resolve issues quickly."* |
| *"We built our own custom Large Language Model from scratch."* | Building an LLM from scratch requires millions of dollars. | *"We integrated Google's state-of-the-art Gemini 2.5 Flash model and engineered 15 custom domain tools to ground it in our local database."* |
| *"We guarantee exact financial and energy savings."* | Future savings depend on actual operational implementation. | *"Our recommendation engine models projected savings based on baseline threshold deltas and standard utility rate formulas."* |
| *"We have a fully working 3D BIM digital twin."* | The 3D view in the frontend is currently a visual conceptual mockup. | *"Our core focus is on time-series telemetry and ML; interactive 3D BIM rendering is part of our future roadmap."* |

---

## 24. Technical Glossary You Must Know

- **API (Application Programming Interface)**: The bridge allowing the frontend to send and receive structured data from the backend.
- **REST (Representational State Transfer)**: Standard architectural pattern using HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).
- **ORM (Object-Relational Mapping)**: A tool (SQLAlchemy) that lets Python code talk to database tables using Python classes instead of writing raw SQL.
- **JWT (JSON Web Token)**: A secure, cryptographically signed token stored in the browser to verify who you are on every request.
- **RBAC (Role-Based Access Control)**: Restricting features based on user roles (`SUPER_ADMIN` vs `ADMIN`).
- **Tenant Isolation**: Ensuring Customer A's data can never be seen or accessed by Customer B.
- **Telemetry**: Automated time-series sensor measurements (kWh, Litres, AQI) collected at regular intervals.
- **Baseline**: The normal, expected operational value for a sensor during standard working conditions.
- **Threshold Delta**: The percentage deviation above baseline that triggers a Warning (+15%) or Critical (+30%) alert.
- **Diurnal Cycle**: The recurring 24-hour daily human rhythm (high daytime usage, low nighttime usage).
- **Z-Score**: A statistical measure of how many standard deviations a reading is away from the 24-hour mean.
- **Isolation Forest**: An unsupervised machine learning algorithm that identifies outliers by randomly partitioning feature dimensions.
- **Tool Calling (Function Calling)**: When an LLM like Gemini calls a backend Python function to fetch real database numbers before answering.
- **SQLite VACUUM**: A database maintenance command that defragments the database file and reclaims deleted disk space back to the operating system.

---

## 25. The 5-Minute Quick Revision Sheet

*Review this 5-point cheat sheet immediately before walking up to present!*

1. **What is GreenNexa?**  
   A multi-tenant sustainability platform for universities, hospitals, industries, and municipalities that tracks energy, water, waste, and civic assets, detects anomalies using ML, and assists operators with a multilingual AI assistant.
2. **The Tech Stack in 10 Seconds**:  
   - Frontend: **Next.js 14**, React 18, TypeScript, custom Vanilla CSS (Day/Night + 6 themes).  
   - Backend: **FastAPI** (Python 3.11+), Pydantic v2, PBKDF2 hashing, JWT tokens.  
   - Database: **SQLite** via **SQLAlchemy ORM** (13 normalized tables).  
   - AI/ML: **Statsmodels** (Holt-Winters), **Scikit-Learn** (`IsolationForest`), **Gemini 2.5 Flash** (15 tools).
3. **How Data Enters**:  
   Either from real physical hardware via our authenticated IoT endpoint (`/api/v1/iot/sensor-data`) using device API keys, or from our autonomous 30-second background simulation engine.
4. **How Detection & Guidance Works**:  
   Every reading passes through our Tri-Layer pipeline (Threshold rules $\rightarrow$ 3-Sigma Z-Score $\rightarrow$ Isolation Forest). When a surge is detected, an `AnomalyRecord` is logged, an `AIRecommendation` with rupee savings is created, and a red alert dot illuminates on the dashboard.
5. **The Municipality Difference**:  
   Standard facilities manage indoor physical building blocks; municipalities manage outdoor civic wards and can link external public hospitals and colleges for regional oversight.

---

## 26. Code Traceability Index

If a judge says: *"Show me the code where this is implemented"*, open these exact files:

| Subsystem | Exact File Path in Codebase | Key Function / Class |
| :--- | :--- | :--- |
| **Authentication & Login** | `backend/app/api/v1/auth.py` | `login()`, `verify_password()` |
| **Super Admin Platform** | `backend/app/api/v1/super_admin.py` | `create_full_organisation()`, `reset_user_password()` |
| **Storage Governance** | `backend/app/api/v1/super_admin.py` | `get_platform_storage_overview()`, `safe_vacuum_sqlite()` |
| **Clear All Data (Wipe)**| `backend/app/api/v1/super_admin.py` | `super_admin_clear_all_data()` |
| **Clear Data (Tenant)** | `backend/app/api/v1/organisations.py` | `clear_organisation_operational_data()` |
| **Municipal Wards & Orgs**| `backend/app/api/v1/organisations.py` | `create_municipality_ward()`, `associate_government_org_with_municipality()` |
| **Hardware IoT Gateway** | `backend/app/api/v1/iot.py` | `ingest_sensor_data()`, `_authenticate_iot_device()` |
| **Autonomous Simulator** | `backend/app/services/synthetic_simulator.py` | `SyntheticDataSimulator.run_cycle()`, `_generate_block_reading_value()` |
| **Holt-Winters Forecasting**| `backend/app/services/forecasting.py` | `ForecastingService.generate_forecast()` |
| **Tri-Layer Anomaly Engine**| `backend/app/services/anomaly_detection.py`| `AnomalyDetectionService.process_single_reading()` |
| **Isolation Forest ML** | `backend/app/services/anomaly_ml_service.py` | `AnomalyMLService.score_reading()` |
| **Priority Engine (3+ Alert)**| `backend/app/services/priority_engine.py`| `PriorityEngine.get_high_priority_anomaly()` |
| **Gemini AI Service** | `backend/app/ai/assistant/service.py` | `AssistantService.process_query()` |
| **Gemini 15 Domain Tools**| `backend/app/ai/assistant/gemini_tools.py` | `GEMINI_TOOLS_DECLARATIONS`, `execute_tool_call()` |
| **PDF & CSV Reporting** | `backend/app/services/reporting.py` | `ReportingService.generate_report()` |
| **Header ⋯ Menu Component**| `frontend/src/components/layout/Header.tsx` | `#dashboard-more-menu-dropdown` |
| **Dashboard Style System**| `frontend/src/lib/dashboardStyles.ts` | `DASHBOARD_STYLES`, `resolveSections()` |
| **Theme & Color Engine** | `frontend/src/context/ThemeContext.tsx` | `ThemeProvider`, `COLOR_THEMES` |
| **Red-Dot Notification** | `frontend/src/context/NotificationContext.tsx`| `NotificationProvider`, `refreshNotifications()` |
| **AI Assistant UI** | `frontend/src/components/ai/GreenNexaAssistant.tsx`| `GreenNexaAssistant`, `handleSendMessage()` |

---
*End of GreenNexa Developer & Judge Confidence Guide.*
