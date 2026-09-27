import type { Metadata } from 'next';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import styles from './page.module.css';

export const metadata: Metadata = {
  title: 'How It Works | GreenNexa Architecture & Operational Pipeline',
  description:
    'Explore GreenNexa’s 11-stage operational pipeline: from dual-path ingestion (30s synthetic & authenticated IoT) to tri-layer anomaly detection, priority ranking, and human verification.',
};

const WORKFLOW_STEPS = [
  {
    number: '01',
    icon: '📡',
    title: 'INPUT (Dual-Source Telemetry)',
    desc: 'Sensor telemetry enters GreenNexa via two isolated ingestion pathways: authenticated physical IoT hardware (e.g. ESP32 microcontrollers) transmitting over HTTPS, or an integrated synthetic simulation engine generating realistic facility data.',
    detail: 'Every reading is explicitly tagged with its source ("iot" or "synthetic") to maintain complete operational isolation between demonstration runs and physical hardware streams.',
  },
  {
    number: '02',
    icon: '🛡️',
    title: 'VALIDATE (Authentication & Data Integrity)',
    desc: 'Incoming payloads pass through strict backend Pydantic validation. The system verifies cryptographic device headers (X-Device-ID, X-API-Key), tenant organisation mapping, sensor configuration status, data types, physical ranges, and timestamps.',
    detail: 'Malformed payloads, expired keys, or unauthorized device transmissions are rejected and logged; only validated data enters the analytical pipeline.',
  },
  {
    number: '03',
    icon: '🗄️',
    title: 'STORE (Normalized Database Persistence)',
    desc: 'Validated readings are committed to a normalized SQLite database across 13 core tables, indexing organisation ID, sensor ID, facility block/ward location, numerical value, physical measurement unit, and UTC timestamp.',
    detail: 'Data is strictly isolated per tenant organisation. Historical readings remain immutable for auditing, reporting, and model training.',
  },
  {
    number: '04',
    icon: '🧠',
    title: 'ANALYSE (Time-Series Feature Extraction)',
    desc: 'The analytical engine computes rolling statistical features across active metrics: moving averages, standard deviations, diurnal (24-hour) hour-of-day baselines, and historical comparative boundaries.',
    detail: 'For new organisations or freshly enabled sensors, the engine transparently indicates baseline calibration status until sufficient historical telemetry is accumulated.',
  },
  {
    number: '05',
    icon: '🔍',
    title: 'DETECT (Tri-Layer Anomaly Classification)',
    desc: 'Readings are simultaneously evaluated against three complementary layers: deterministic static threshold boundaries, statistical 3-sigma Z-scores, and Scikit-Learn Isolation Forest machine learning across 8 features.',
    detail: 'Anomalies are classified into LOW, MEDIUM, HIGH, or CRITICAL severity with an automated explanation detailing why the reading triggered the alert.',
  },
  {
    number: '06',
    icon: '📈',
    title: 'FORECAST (Holt-Winters Trend Projection)',
    desc: 'Statsmodels Holt-Winters Exponential Smoothing evaluates historical patterns to project expected near-future trajectories (e.g., 24-hour demand curves) for energy, water, and environmental metrics.',
    detail: 'Forecasts are clearly presented as estimated projections to assist procurement and maintenance planning, never as guaranteed predictions.',
  },
  {
    number: '07',
    icon: '🎯',
    title: 'PRIORITIZE (Smart Priority Engine)',
    desc: 'When multiple active anomalies occur simultaneously (3+ concurrent issues), the Priority Engine evaluates anomaly severity, persistence, and facility impact to rank and spotlight the single most urgent issue.',
    detail: 'This eliminates alert fatigue during facility-wide peak loads or compound incidents, guiding the operator directly to the highest-risk problem.',
  },
  {
    number: '08',
    icon: '💡',
    title: 'RECOMMEND (Contextual Prescriptive Guidance)',
    desc: 'For detected anomalies, GreenNexa generates specific, actionable mitigation steps tailored to the metric, facility block, and fault severity, detailing estimated kWh/m³ and financial savings.',
    detail: 'Recommendations serve as human decision-support tools, outlining clear inspection checkpoints for engineering and maintenance staff.',
  },
  {
    number: '09',
    icon: '🔔',
    title: 'NOTIFY (Red-Dot & Unread State Tracking)',
    desc: 'New anomalies trigger immediate visual indicators, including the global navigation Red-Dot alert and persistent unread tracking in the database (event_read_states) with block and ward attribution.',
    detail: 'Alert deduplication prevents repetitive notifications for ongoing events, while unread badges ensure critical incidents remain highlighted until acknowledged.',
  },
  {
    number: '10',
    icon: '👷',
    title: 'ACT (Human Operator Resolution)',
    desc: 'The facility engineer or municipal officer reviews the alert via the dashboard (Executive, Operations, Analytics, or Command Center) or queries the Gemini 2.5 Flash assistant, and dispatches field personnel.',
    detail: 'The human operator always remains in the loop. GreenNexa does not claim to autonomously repair physical facility infrastructure.',
  },
  {
    number: '11',
    icon: '✅',
    title: 'VERIFY (Closed-Loop Baseline Confirmation)',
    desc: 'Following physical intervention (such as closing an isolation valve or replacing a clogged filter), subsequent 30-second telemetry streams confirm that metrics have returned to nominal baselines, closing the loop.',
    detail: 'Closed-loop verification provides timestamped audit logs confirming whether the physical action successfully resolved the operational fault.',
  },
];

const WATER_SPIKE_STORY = [
  {
    step: '01',
    title: 'Telemetry Surge Detected',
    desc: 'At 02:15 AM, Flow Meter W-102 in Block B detects water flow surging from a nominal night baseline of 22 m³/h to 88 m³/h.',
  },
  {
    step: '02',
    title: 'Ingestion & Validation',
    desc: 'The incoming HTTP payload is verified against device credentials (X-Device-ID / X-API-Key), validated against schema limits, and stored in SQLite within milliseconds.',
  },
  {
    step: '03',
    title: 'Tri-Layer Anomaly Detection',
    desc: 'The anomaly engine flags the event: hard threshold exceeded, statistical Z-score > 4.2σ, and Isolation Forest score -0.38. Severity is classified as HIGH.',
  },
  {
    step: '04',
    title: 'Historical Context & Forecasting',
    desc: 'Historical baselines identify this as an abnormal nocturnal draw. Holt-Winters forecasting projects significant cumulative volumetric loss over the next 12 hours if unaddressed.',
  },
  {
    step: '05',
    title: 'Priority Engine Activation',
    desc: 'With 3 minor environmental warnings active elsewhere, the Priority Engine evaluates risk scores and spotlights the Block B water surge as Priority #1.',
  },
  {
    step: '06',
    title: 'Prescriptive Recommendation Generated',
    desc: 'The engine generates an actionable recommendation: "Urgent: Nocturnal water surge in Block B. Inspect main riser isolation valve and secondary booster pumps. Estimated loss: ~66 m³/h (~₹3,200/hr)."',
  },
  {
    step: '07',
    title: 'Red-Dot Notification',
    desc: 'The Red-Dot indicator illuminates in the header navigation bar, alerting the duty operator to the unread priority issue.',
  },
  {
    step: '08',
    title: 'Human Operational Action',
    desc: 'The duty operator reviews the priority card, dispatches a night maintenance technician to Block B, who discovers a ruptured supply flange and isolates the riser valve.',
  },
  {
    step: '09',
    title: 'Closed-Loop Verification',
    desc: 'At 02:42 AM, subsequent 30-second telemetry cycles confirm flow has dropped back to 21.5 m³/h. The system logs the anomaly as resolved, completing the loop.',
  },
];

const TECH_STACK_ITEMS = [
  {
    category: 'Frontend Client',
    title: 'Next.js 14 & React 18',
    desc: 'TypeScript, App Router, custom Vanilla CSS design tokens, responsive layouts, and React Context-based state management.',
  },
  {
    category: 'Backend API',
    title: 'FastAPI & Python 3.11+',
    desc: 'Asynchronous REST architecture, Pydantic v2 data models, SQLAlchemy 2.0 ORM, and JWT bearer authentication.',
  },
  {
    category: 'Database Storage',
    title: 'SQLite (13 Normalized Tables)',
    desc: 'Multi-tenant schema, physical SQLite .db file size monitoring, logical org byte attribution, and SQLite VACUUM maintenance.',
  },
  {
    category: 'AI & Analytics',
    title: 'Statsmodels & Scikit-Learn',
    desc: 'Holt-Winters Exponential Smoothing for 24h diurnal forecasting, statistical 3-sigma Z-scores, and 8-feature Isolation Forest ML.',
  },
  {
    category: 'Conversational AI',
    title: 'Gemini 2.5 Flash & GenAI SDK',
    desc: 'Conversational assistant with 15 domain tool bindings, multilingual dialogue (English, Hinglish, Odia), and safe offline fallback.',
  },
  {
    category: 'IoT Ingestion',
    title: 'Authenticated HTTP Ingestion',
    desc: 'Dedicated endpoint (/api/v1/iot/sensor-data) authenticated with X-Device-ID and X-API-Key headers and sensor catalog verification.',
  },
];

export default function HowItWorksPage() {
  return (
    <>
      <Header />
      <main>
        {/* Page Hero */}
        <section className={styles.pageHero}>
          <div className="container">
            <span className="section-label">⚙️ Operational Architecture</span>
            <h1 className="section-title">
              How GreenNexa works
            </h1>
            <p className="section-subtitle">
              From raw sensor telemetry to prioritized operational action — a closed-loop intelligence
              pipeline operating on a rapid 30-second telemetry cycle.
            </p>
          </div>
        </section>

        {/* Update Cycle Callout */}
        <section className="section-sm bg-subtle">
          <div className="container">
            <div className={styles.cycleBox}>
              <span className={styles.cycleIcon}>⏱️</span>
              <div>
                <strong>30-Second Continuous Cycle</strong>
                <p>
                  GreenNexa processes sensor telemetry every 30 seconds across enabled facility modules —
                  validating incoming payloads, updating rolling statistical baselines, evaluating
                  multi-model anomalies, prioritizing urgent risks, and refreshing the operational dashboard in real time.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Dual Ingestion Pathways */}
        <section className="section">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Data Ingestion Pathways</span>
              <h2 className="section-title">Two Dedicated Telemetry Pathways</h2>
              <p className="section-subtitle">
                GreenNexa maintains strict isolation between physical IoT telemetry and synthetic evaluation data.
              </p>
            </div>
            <div className={styles.pathsGrid}>
              {/* Path A */}
              <div className={styles.pathCard}>
                <span className={styles.pathBadge} style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#2563eb' }}>
                  PATH A — SYNTHETIC SIMULATION
                </span>
                <h3 className={styles.storyTitle}>Demo Mode Simulator</h3>
                <p className={styles.storyDesc}>
                  Designed for demonstrations, feature evaluations, and scenario testing without requiring physical sensors. Runs on an isolated 30-second cycle scoped strictly to the active organisation.
                </p>
                <div className={styles.pathFlow}>
                  <div className={styles.pathStep}>1. Admin toggles Demo Mode ON</div>
                  <div className={styles.pathStep}>2. In-memory simulator activates</div>
                  <div className={styles.pathStep}>3. 30-second monotonic cycle triggers</div>
                  <div className={styles.pathStep}>4. Realistic diurnal readings generated for enabled sensors</div>
                  <div className={styles.pathStep}>5. Readings stored in SQLite (source: "synthetic")</div>
                  <div className={styles.pathStep}>6. Ingested into identical downstream analytics pipeline</div>
                </div>
              </div>

              {/* Path B */}
              <div className={styles.pathCard}>
                <span className={styles.pathBadge} style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#16a34a' }}>
                  PATH B — REAL HARDWARE IOT
                </span>
                <h3 className={styles.storyTitle}>Authenticated IoT Ingestion</h3>
                <p className={styles.storyDesc}>
                  Production telemetry transmitted by physical microcontrollers (e.g., ESP32, industrial gateways, or smart digital meters) over secure HTTPS POST endpoints.
                </p>
                <div className={styles.pathFlow}>
                  <div className={styles.pathStep}>1. Physical IoT device captures sensor measurement</div>
                  <div className={styles.pathStep}>2. Transmits HTTP POST to /api/v1/iot/sensor-data</div>
                  <div className={styles.pathStep}>3. Headers verified: X-Device-ID &amp; X-API-Key</div>
                  <div className={styles.pathStep}>4. Schema &amp; organisation sensor catalog validated</div>
                  <div className={styles.pathStep}>5. Readings stored in SQLite (source: "iot")</div>
                  <div className={styles.pathStep}>6. Ingested into identical downstream analytics pipeline</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Step-by-Step 11-Stage Pipeline */}
        <section className="section bg-subtle">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">End-to-End Pipeline</span>
              <h2 className="section-title">The Complete 11-Stage Operational Workflow</h2>
              <p className="section-subtitle">
                INPUT → VALIDATE → STORE → ANALYSE → DETECT → FORECAST → PRIORITIZE → RECOMMEND → NOTIFY → ACT → VERIFY
              </p>
            </div>
            <div className={styles.stepsContainer}>
              {WORKFLOW_STEPS.map(({ number, icon, title, desc, detail }, idx) => (
                <div key={number} className={styles.step}>
                  <div className={styles.stepLeft}>
                    <div className={styles.stepNumber}>{number}</div>
                    {idx < WORKFLOW_STEPS.length - 1 && <div className={styles.stepLine} />}
                  </div>
                  <div className={styles.stepRight}>
                    <div className={styles.stepHeader}>
                      <span className={styles.stepIcon}>{icon}</span>
                      <h3 className={styles.stepTitle}>{title}</h3>
                    </div>
                    <p className={styles.stepDesc}>{desc}</p>
                    <div className={styles.stepDetail}>
                      <span className={styles.detailIcon}>ℹ️</span>
                      <span>{detail}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section 9: Water-Spike Operational Walkthrough */}
        <section className="section">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Operational Walkthrough</span>
              <h2 className="section-title">Real-World Incident: Water Consumption Surge</h2>
              <p className="section-subtitle">
                An end-to-end example demonstrating how GreenNexa handles an abnormal flow event from initial detection to human verification.
              </p>
            </div>
            <div className={styles.storyContainer}>
              {WATER_SPIKE_STORY.map(({ step, title, desc }, idx) => (
                <div key={step} className={styles.storyStep}>
                  <div className={styles.storyLeft}>
                    <div className={styles.storyBadge}>{step}</div>
                    {idx < WATER_SPIKE_STORY.length - 1 && <div className={styles.storyLine} />}
                  </div>
                  <div className={styles.storyRight}>
                    <div className={styles.storyHeader}>
                      <h4 className={styles.storyTitle}>{title}</h4>
                    </div>
                    <p className={styles.storyDesc}>{desc}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="info-box" style={{ marginTop: 'var(--space-8)' }}>
              <strong>Human-in-the-Loop Architecture:</strong> GreenNexa provides actionable decision
              support, predictive risk analysis, and prescriptive guidance. The platform does not claim
              to automatically or autonomously repair physical infrastructure. Trained facility operators
              and maintenance engineers always remain in control to inspect hardware, execute repairs,
              and verify operational safety.
            </div>
          </div>
        </section>

        {/* Section 10: Verified Architecture Stack */}
        <section className="section bg-subtle">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Technology Architecture</span>
              <h2 className="section-title">Verified Implementation Stack</h2>
              <p className="section-subtitle">
                Technologies verified directly in the implemented production codebase.
              </p>
            </div>
            <div className={styles.techGrid}>
              {TECH_STACK_ITEMS.map(({ category, title, desc }) => (
                <div key={title} className={styles.techCard}>
                  <div className={styles.techCategory}>{category}</div>
                  <h3 className={styles.techTitle}>{title}</h3>
                  <p className={styles.techDesc}>{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Technical Honesty & Limitations */}
        <section className="section-sm">
          <div className="container">
            <div className="info-box">
              <strong>Technical Honesty &amp; Operational Disclosures:</strong>
              <ul style={{ listStyleType: 'disc', paddingLeft: 'var(--space-5)', marginTop: 'var(--space-2)' }}>
                <li><strong>Simulated Data:</strong> Telemetry in Demo Mode is synthetically generated on a 30-second cycle for evaluation purposes.</li>
                <li><strong>Modelled What-If Scenarios:</strong> What-If simulations are mathematical approximations of operational changes, not guaranteed future outcomes.</li>
                <li><strong>Forecast Reliability:</strong> Holt-Winters projection fidelity scales directly with historical telemetry depth.</li>
                <li><strong>Storage Attribution:</strong> Organisation storage usage shown in Super Admin Manage Storage is a logical attribution calculated within the shared SQLite database.</li>
                <li><strong>Future Placeholders:</strong> Advanced 3D/BIM facility digital twins and OTA device firmware updates, where noted on the roadmap, remain conceptual placeholders.</li>
              </ul>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
