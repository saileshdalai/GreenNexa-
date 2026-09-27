import type { Metadata } from 'next';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import styles from './page.module.css';

export const metadata: Metadata = {
  title: 'About GreenNexa | Sustainable Facility Intelligence Platform',
  description:
    'Learn how GreenNexa combines operational IoT data, tri-layer anomaly detection, Holt-Winters forecasting, and Gemini 2.5 Flash conversational intelligence into a closed-loop decision system.',
};

const SUPPORTED_FACILITIES = [
  { icon: '🎓', name: 'Colleges & Universities' },
  { icon: '🏥', name: 'Hospitals & Healthcare' },
  { icon: '🏢', name: 'Corporate Campuses & Offices' },
  { icon: '🏪', name: 'Commercial Complexes & Retail' },
  { icon: '🏘️', name: 'Residential Townships' },
  { icon: '🏛️', name: 'Municipalities & Civic Wards' },
];

const OPERATIONAL_LOOP = [
  {
    step: '01',
    name: 'SENSE',
    title: 'Telemetry Ingestion',
    desc: 'Ingests readings every 30 seconds via authenticated HTTP IoT endpoints (X-Device-ID + X-API-Key) or isolated module-scoped synthetic simulators for active sensors.',
  },
  {
    step: '02',
    name: 'UNDERSTAND',
    title: 'Tri-Layer Analytics',
    desc: 'Processes streams through hard threshold limits, statistical 3-sigma Z-score rolling baselines, Scikit-Learn Isolation Forest ML, and Holt-Winters 24h diurnal forecasting.',
  },
  {
    step: '03',
    name: 'DECIDE',
    title: 'Priority & Prescriptions',
    desc: 'When concurrent anomalies arise, the Priority Engine isolates the single most urgent issue and generates contextual recommendations with estimated kWh, m³, or cost savings.',
  },
  {
    step: '04',
    name: 'ACT',
    title: 'Operator Resolution',
    desc: 'Facility operators review clear priority cards across 4 dashboard styles, interact with the Gemini 2.5 Flash conversational assistant, and dispatch maintenance teams.',
  },
  {
    step: '05',
    name: 'VERIFY',
    title: 'Closed-Loop Validation',
    desc: 'Subsequent 30-second telemetry cycles stream continuously, mathematically confirming whether physical interventions restored normal baseline operations.',
  },
];

const WHY_ITEMS = [
  {
    icon: '⚡',
    title: 'An Operational Decision System (Beyond Static Dashboards)',
    body: 'Most facility software stops at visual charts and passive graphs. GreenNexa treats the dashboard as merely the user-facing presentation layer of an end-to-end operational decision system. It continuously bridges raw sensor telemetry, AI/ML analytics, predictive forecasting, priority evaluation, and prescriptive recommendations into guided human operational action.',
  },
  {
    icon: '📡',
    title: 'Dual-Path Ingestion: Authenticated IoT & 30-Second Simulation',
    body: 'Facilities can stream physical hardware telemetry (such as ESP32 microcontrollers) over authenticated HTTPS using unique device IDs and secret keys. For evaluation, testing, or demonstrations, an isolated 30-second synthetic simulator models realistic diurnal consumption curves and injected faults without polluting production data.',
  },
  {
    icon: '🔍',
    title: 'Tri-Layer Anomaly Detection (Rules, Statistics & Machine Learning)',
    body: 'Operational failures rarely conform to simple static rules. GreenNexa combines deterministic threshold boundaries, statistical 3-sigma rolling Z-score deviations, and unsupervised Scikit-Learn Isolation Forest algorithms across 8 features to detect subtle equipment degradation, leaks, and demand spikes before catastrophic failures occur.',
  },
  {
    icon: '🎯',
    title: 'The Priority Engine: Eliminating Multi-Anomaly Alert Fatigue',
    body: 'When 3 or more anomalies occur concurrently across facility systems, operators risk alert fatigue. GreenNexa’s Priority Engine automatically evaluates risk severity, persistence, and facility impact to isolate and spotlight the single most critical issue, keeping operators focused on what matters most.',
  },
  {
    icon: '🤖',
    title: 'Conversational Intelligence: Gemini 2.5 Flash with 15 Domain Tools',
    body: 'Facility managers and engineers can query operational status in natural language using English, Hinglish, Odia, or Roman Odia. Powered by Google GenAI SDK and Gemini 2.5 Flash, GreenNexa AI leverages 15 specialized domain tools to inspect real-time metrics, anomalies, forecasts, and What-If scenarios with safe offline fallback.',
  },
  {
    icon: '🏛️',
    title: 'Municipal Civic Monitoring & Government-Only Association',
    body: 'In addition to standard facility modules, municipal administrations gain dedicated civic infrastructure monitoring across Wards—including Street Lighting, Roads & Infrastructure, Parks & Playgrounds, and Drainage & Sewage. GreenNexa enforces strict governance hierarchy: only verified Government organisations can associate with a municipality.',
  },
];

const ARCHITECTURE_STACK = [
  {
    category: 'Frontend Client',
    title: 'Next.js 14 App Router',
    desc: 'React 18, TypeScript, custom Vanilla CSS design tokens, responsive layouts, and React Context-based state management.',
  },
  {
    category: 'Backend Services',
    title: 'FastAPI & Python 3.11+',
    desc: 'High-performance asynchronous REST API, Pydantic v2 schema validation, SQLAlchemy 2.0 ORM, and JWT bearer authentication.',
  },
  {
    category: 'Database Storage',
    title: 'SQLite (13 Normalized Tables)',
    desc: 'Strict multi-tenant schema isolation, historical immutable telemetry, physical file-size monitoring, and logical org attribution.',
  },
  {
    category: 'AI & Analytics',
    title: 'Statsmodels & Scikit-Learn',
    desc: 'Holt-Winters Exponential Smoothing for 24h diurnal forecasting, statistical 3-sigma Z-scores, and 8-feature Isolation Forest ML.',
  },
  {
    category: 'Conversational AI',
    title: 'Gemini 2.5 Flash & GenAI SDK',
    desc: 'Natural language interface with 15 live domain tool bindings, multilingual dialogue, What-If simulation, and graceful offline fallback.',
  },
  {
    category: 'IoT Security',
    title: 'Authenticated Ingestion',
    desc: 'Dedicated HTTP endpoints (/api/v1/iot/sensor-data) with X-Device-ID and X-API-Key verification, rate-limiting, and sensor catalog validation.',
  },
];

export default function AboutPage() {
  return (
    <>
      <Header />
      <main>
        {/* Page Hero */}
        <section className={styles.pageHero}>
          <div className="container">
            <span className="section-label">About GreenNexa</span>
            <h1 className="section-title">
              From facility telemetry to<br />
              <span style={{ color: 'var(--clr-primary)' }}>operational intelligence</span>
            </h1>
            <p className="section-subtitle">
              GreenNexa is an AI-powered sustainable facility intelligence platform for institutions
              and municipalities. Far beyond a passive visualization dashboard, GreenNexa connects
              operational data, multi-model AI/ML, forecasting, priority ranking, and conversational
              intelligence into a closed-loop operational decision system.
            </p>
          </div>
        </section>

        {/* Supported Facilities */}
        <section className="section-sm bg-subtle">
          <div className="container">
            <h2 className={styles.smallTitle}>Engineered for modern institutions & civic administrations</h2>
            <div className={styles.facilityGrid}>
              {SUPPORTED_FACILITIES.map(({ icon, name }) => (
                <div key={name} className={styles.facilityChip}>
                  <span>{icon}</span>
                  <span>{name}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Operational Decision Loop */}
        <section className="section">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">The Operational Decision Loop</span>
              <h2 className="section-title">SENSE → UNDERSTAND → DECIDE → ACT → VERIFY</h2>
              <p className="section-subtitle">
                How GreenNexa turns raw sensor telemetry into validated operational resolutions.
              </p>
            </div>
            <div className={styles.loopGrid}>
              {OPERATIONAL_LOOP.map(({ step, name, title, desc }) => (
                <div key={step} className={styles.loopCard}>
                  <div className={styles.loopBadge}>{step}</div>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--clr-primary)' }}>{name}</div>
                  <h3 className={styles.loopTitle}>{title}</h3>
                  <p className={styles.loopDesc}>{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Core Pillars / Why Items */}
        <section className="section bg-subtle">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Platform Architecture</span>
              <h2 className="section-title">Why GreenNexa exists</h2>
              <p className="section-subtitle">
                Built to solve the operational gap between fragmented telemetry and decisive facility action.
              </p>
            </div>
            <div className={styles.whyGrid}>
              {WHY_ITEMS.map(({ icon, title, body }) => (
                <div key={title} className={styles.whyCard}>
                  <div className={styles.whyIcon}>{icon}</div>
                  <div>
                    <h3 className={styles.whyTitle}>{title}</h3>
                    <p className={styles.whyBody}>{body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Verified Architecture Stack */}
        <section className="section">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Under The Hood</span>
              <h2 className="section-title">Verified technology architecture</h2>
              <p className="section-subtitle">
                Built with modern, open standards verified directly in the implemented production codebase.
              </p>
            </div>
            <div className={styles.techGrid}>
              {ARCHITECTURE_STACK.map(({ category, title, desc }) => (
                <div key={title} className={styles.techCard}>
                  <div className={styles.techCategory}>{category}</div>
                  <h3 className={styles.techTitle}>{title}</h3>
                  <p className={styles.techDesc}>{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Technical Honesty Disclaimer */}
        <section className="section-sm">
          <div className="container">
            <div className="info-box">
              <strong>Operational Transparency &amp; Verification:</strong> GreenNexa is an AI-powered
              decision-support intelligence platform, not an autonomous facility control system.
              Forecasts, anomaly classifications, and What-If scenario projections are algorithmic
              estimations whose accuracy scales with historical telemetry depth. Facility managers
              and maintenance teams always remain in the loop to inspect physical infrastructure,
              authorize actions, and verify operational conditions.
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
