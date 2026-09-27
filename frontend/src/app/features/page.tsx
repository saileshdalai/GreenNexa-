import type { Metadata } from 'next';
import Link from 'next/link';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import styles from './page.module.css';

export const metadata: Metadata = {
  title: 'Features | GreenNexa Facility Intelligence',
  description:
    'Explore GreenNexa’s implemented capabilities: 8 core facility modules, 4 municipality civic modules, tri-layer anomaly detection, priority engine, Holt-Winters forecasting, and Gemini 2.5 Flash assistant.',
};

const CORE_MODULES = [
  {
    icon: '⚡',
    category: 'Core Module',
    title: 'Energy Intelligence',
    desc: 'Monitor real-time electricity consumption (kWh), phase loads, and diurnal baselines. Track peak demand intervals, detect electrical overloads, and view Statsmodels Holt-Winters 24-hour predictive forecasts.',
    tags: ['kWh Tracking', 'Peak Demand', 'Diurnal Baselines', 'Holt-Winters'],
  },
  {
    icon: '💧',
    category: 'Core Module',
    title: 'Water Supply Intelligence',
    desc: 'Track volumetric flow rates (m³/h), cumulative consumption, and storage tank levels across facility blocks. Automated anomaly detection flags sudden spikes and continuous off-hour flow indicative of pipe leaks.',
    tags: ['Flow Rates (m³/h)', 'Consumption Spikes', 'Leakage Detection', 'Block Allocation'],
  },
  {
    icon: '♻️',
    category: 'Core Module',
    title: 'Waste Management Intelligence',
    desc: 'Monitor daily waste generation rates (kg) with segregation tracking across organic, recyclable, and hazardous streams. Track bin fill levels and plan collection logistics to reduce landfill overhead.',
    tags: ['Generation (kg)', 'Waste Segregation', 'Collection Schedules', 'Landfill Reduction'],
  },
  {
    icon: '🌬️',
    category: 'Core Module',
    title: 'Air Quality & Environment',
    desc: 'Continuous monitoring of indoor and ambient environmental quality: Air Quality Index (AQI), PM2.5, PM10, CO₂ concentration (ppm), ambient temperature (°C), and relative humidity (%).',
    tags: ['AQI & Particulates', 'CO₂ Monitoring', 'Temperature & Humidity', 'Indoor Safety'],
  },
  {
    icon: '🚗',
    category: 'Core Module',
    title: 'Traffic & Parking Intelligence',
    desc: 'Real-time vehicle ingress/egress monitoring, parking bay occupancy rates (%), gate throughput velocities, and peak congestion window detection across campus transit points.',
    tags: ['Bay Occupancy %', 'Vehicle Flow', 'Peak Congestion', 'Transit Analytics'],
  },
  {
    icon: '🏛️',
    category: 'Core Module',
    title: 'Municipal & Facility Assets',
    desc: 'Centralized registry for facility HVAC units, pumps, transformers, and civic assets. Track operational health status, scheduled maintenance intervals, and lifecycle depreciation metrics.',
    tags: ['Asset Registry', 'Uptime Tracking', 'Maintenance Logs', 'Depreciation'],
  },
  {
    icon: '🛡️',
    category: 'Core Module',
    title: 'Safety & Incident Management',
    desc: 'Automated hazard detection, emergency response readiness metrics, incident logging with severity grading (Low to Critical), and historical resolution audit trails.',
    tags: ['Hazard Alerts', 'Severity Grading', 'Emergency Readiness', 'Audit Trails'],
  },
  {
    icon: '🌿',
    category: 'Core Module',
    title: 'Climate & Carbon Footprint',
    desc: 'Track facility carbon emissions (kg CO₂e), solar irradiance metrics, heat stress index, and environmental footprint indicators aligned with institutional sustainability goals.',
    tags: ['Carbon Footprint', 'Solar Irradiance', 'Heat Stress Index', 'Sustainability Score'],
  },
];

const CIVIC_MODULES = [
  {
    icon: '💡',
    category: 'Municipality Only',
    title: 'Street Lighting (Civic)',
    desc: 'Ward-by-ward street lighting operational uptime, automated astronomical dusk-to-dawn scheduling, energy usage, and instant dark-spot or circuit fault alerts.',
    tags: ['Municipality Only', 'Ward-Level Uptime', 'Circuit Faults', 'Auto Scheduling'],
  },
  {
    icon: '🛣️',
    category: 'Municipality Only',
    title: 'Roads & Infrastructure (Civic)',
    desc: 'Civic transit corridor tracking, road surface quality logging, pothole and structural damage reports, and civic maintenance work order coordination.',
    tags: ['Municipality Only', 'Corridor Monitoring', 'Pothole Reports', 'Work Orders'],
  },
  {
    icon: '🌳',
    category: 'Municipality Only',
    title: 'Parks & Playgrounds (Civic)',
    desc: 'Public recreation space management, urban green cover index calculation, recreational facility amenity status, and automated landscape irrigation scheduling.',
    tags: ['Municipality Only', 'Green Cover Index', 'Public Amenities', 'Smart Irrigation'],
  },
  {
    icon: '🌊',
    category: 'Municipality Only',
    title: 'Drainage & Sewage (Civic)',
    desc: 'Stormwater drainage runoff capacity, sewer line flow velocity monitoring, urban flood risk detection, and automated blockage detection across municipal wards.',
    tags: ['Municipality Only', 'Runoff Levels', 'Flood Risk Alerts', 'Blockage Detection'],
  },
];

const AI_ANALYTICS_FEATURES = [
  {
    icon: '🔍',
    category: 'AI / ML',
    title: 'Tri-Layer Anomaly Detection',
    desc: 'Fuses deterministic threshold limits, statistical rolling 3-sigma Z-scores, and Scikit-Learn Isolation Forest machine learning (8 features) to identify and classify anomalies as LOW, MEDIUM, HIGH, or CRITICAL.',
    tags: ['Isolation Forest', '3-Sigma Z-Score', 'Static Thresholds', 'Severity Ranking'],
  },
  {
    icon: '🎯',
    category: 'AI / ML',
    title: 'Intelligent Priority Engine',
    desc: 'When 3 or more concurrent anomalies occur across facility modules, the Priority Engine evaluates metric urgency, persistence, and operational risk to focus the operator on the single most critical issue.',
    tags: ['Multi-Anomaly Ranking', 'Operator Focus', 'Urgency Scoring', 'Fatigue Reduction'],
  },
  {
    icon: '📈',
    category: 'AI / ML',
    title: 'Time-Series Forecasting',
    desc: 'Applies Statsmodels Holt-Winters Exponential Smoothing to capture diurnal (24-hour) cycles and project near-future energy and water trajectories. Projections are clearly presented as estimated forecasts.',
    tags: ['Holt-Winters', '24h Diurnal Cycles', 'Trend Projection', 'Estimated Output'],
  },
  {
    icon: '💡',
    category: 'AI / ML',
    title: 'Contextual Prescriptive Recommendations',
    desc: 'Generates actionable, evidence-based mitigation steps tailored to the specific metric, facility block, and fault severity. Quantifies estimated kWh/m³ savings and financial impact for maintenance crews.',
    tags: ['Prescriptive Actions', 'Estimated Savings', 'Block Context', 'Decision Support'],
  },
  {
    icon: '🤖',
    category: 'Conversational AI',
    title: 'GreenNexa AI Assistant',
    desc: 'Gemini 2.5 Flash-powered operational assistant using 15 specialized domain tools to inspect real-time metrics, anomalies, forecasts, recommendations, block comparisons, and What-If scenarios in English, Hinglish, and Odia.',
    tags: ['Gemini 2.5 Flash', '15 Domain Tools', 'Multilingual', 'Offline Fallback'],
  },
];

const PLATFORM_FEATURES = [
  {
    icon: '📡',
    category: 'Data Ingestion',
    title: 'Dual Data Ingestion Pipeline',
    desc: 'Ingest real-world data from physical hardware (ESP32 microcontrollers) via authenticated HTTP POST endpoints (X-Device-ID, X-API-Key) or activate Demo Mode for realistic, module-scoped 30-second synthetic simulations.',
    tags: ['Authenticated IoT', 'HTTP Ingestion', '30s Demo Simulator', 'Strict Validation'],
  },
  {
    icon: '🔔',
    category: 'Operations',
    title: 'Red-Dot Notifications & Read Tracking',
    desc: 'Real-time visual alert indicator in the navigation bar showing unread anomalies and system messages. Persistent database tracking (event_read_states) ensures alerts remain visible until acknowledged.',
    tags: ['Red-Dot Indicator', 'Read/Seen State', 'Tenant Scoped', 'Instant Awareness'],
  },
  {
    icon: '📑',
    category: 'Reporting',
    title: 'Audit, Compliance & Export Reports',
    desc: 'Export operational performance, anomaly histories, and sustainability data into structured CSV or publication-ready PDF formats generated server-side using ReportLab.',
    tags: ['ReportLab PDF', 'CSV Export', 'Historical Audits', 'RBAC-Enforced'],
  },
  {
    icon: '🏛️',
    category: 'Governance',
    title: 'Municipality & Ward Hierarchy',
    desc: 'Hierarchical governance model supporting urban municipalities and designated civic wards. Enforces a strict Government-only association policy—private entities cannot link to municipal authorities.',
    tags: ['Ward Hierarchy', 'Gov-Only Policy', 'Civic Aggregation', 'Multi-Tenant'],
  },
  {
    icon: '💾',
    category: 'Administration',
    title: 'Super Admin Storage Management',
    desc: 'Real-time database diagnostics displaying physical SQLite .db disk usage, table-level metrics, and logical organisation attribution grouped into Government vs Private sectors with SQLite VACUUM optimization.',
    tags: ['Physical Disk Size', 'Logical Attribution', 'Gov vs Private', 'SQLite VACUUM'],
  },
  {
    icon: '🎨',
    category: 'Presentation',
    title: 'Dashboard Customization & Themes',
    desc: 'Tailor the operational interface with 4 distinct Dashboard Styles (Executive, Operations, Analytics, Command Center), 6 color themes (Emerald, Ocean Blue, Indigo, Teal, Graphite, Amber), and instant Day/Night mode.',
    tags: ['4 Styles', '6 Themes', 'Day / Night Mode', 'Visual Density'],
  },
  {
    icon: '🔐',
    category: 'Security',
    title: 'Multi-Tenant Role-Based Access Control',
    desc: 'Enforces strict data isolation. SUPER_ADMIN manages global organisations, storage, and platform settings. Organisation ADMINs are strictly isolated to their own facility dashboard, sensors, reports, and Demo Mode.',
    tags: ['RBAC', 'Tenant Isolation', 'SUPER_ADMIN & ADMIN', 'JWT & Bcrypt'],
  },
];

export default function FeaturesPage() {
  return (
    <>
      <Header />
      <main>
        {/* Page Hero */}
        <section className={styles.pageHero}>
          <div className="container">
            <span className="section-label">✦ Implemented Platform Capabilities</span>
            <h1 className="section-title">
              Complete operational intelligence for<br />
              <span style={{ color: 'var(--clr-primary)' }}>facilities &amp; civic administrations</span>
            </h1>
            <p className="section-subtitle">
              From authenticated IoT streams and 30-second simulation to tri-layer anomaly detection,
              priority evaluation, and conversational AI — explore GreenNexa’s fully implemented capabilities.
            </p>
          </div>
        </section>

        {/* Section 1: 8 Core Facility Modules */}
        <section className="section">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Core Modules</span>
              <h2 className="section-title">8 Core Facility Monitoring Modules</h2>
              <p className="section-subtitle">
                Universal monitoring and intelligence modules implemented for institutional, commercial, and residential facilities.
              </p>
            </div>
            <div className={styles.featuresGrid}>
              {CORE_MODULES.map(({ icon, category, title, desc, tags }) => (
                <div key={title} className={styles.featureCard}>
                  <div className={styles.featureCardTop}>
                    <div className={styles.featureIcon}>{icon}</div>
                    <span className={styles.featureCategory}>{category}</span>
                  </div>
                  <h3 className={styles.featureTitle}>{title}</h3>
                  <p className={styles.featureDesc}>{desc}</p>
                  <div className={styles.featureTags}>
                    {tags.map((tag) => (
                      <span key={tag} className={styles.tag}>{tag}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section 2: 4 Civic Modules (Municipality Specific) */}
        <section className="section bg-subtle">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Civic Infrastructure Layer</span>
              <h2 className="section-title">4 Municipality-Specific Civic Modules</h2>
              <p className="section-subtitle">
                Specialized urban infrastructure modules available exclusively when an organisation is configured as a Municipality. These civic modules do not apply to standard private facilities.
              </p>
            </div>
            <div className={styles.featuresGrid}>
              {CIVIC_MODULES.map(({ icon, category, title, desc, tags }) => (
                <div key={title} className={styles.featureCard}>
                  <div className={styles.featureCardTop}>
                    <div className={styles.featureIcon}>{icon}</div>
                    <span className={styles.featureCategory} style={{ color: 'var(--clr-warning)', background: 'rgba(245, 158, 11, 0.15)' }}>{category}</span>
                  </div>
                  <h3 className={styles.featureTitle}>{title}</h3>
                  <p className={styles.featureDesc}>{desc}</p>
                  <div className={styles.featureTags}>
                    {tags.map((tag) => (
                      <span key={tag} className={styles.tag}>{tag}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section 3: AI / ML & Decision Engine */}
        <section className="section">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Predictive &amp; Prescriptive Engine</span>
              <h2 className="section-title">AI, Machine Learning &amp; Decision Intelligence</h2>
              <p className="section-subtitle">
                Multi-model analytics combining statistical rigour, machine learning, priority evaluation, and conversational intelligence.
              </p>
            </div>
            <div className={styles.featuresGrid}>
              {AI_ANALYTICS_FEATURES.map(({ icon, category, title, desc, tags }) => (
                <div key={title} className={styles.featureCard}>
                  <div className={styles.featureCardTop}>
                    <div className={styles.featureIcon}>{icon}</div>
                    <span className={styles.featureCategory}>{category}</span>
                  </div>
                  <h3 className={styles.featureTitle}>{title}</h3>
                  <p className={styles.featureDesc}>{desc}</p>
                  <div className={styles.featureTags}>
                    {tags.map((tag) => (
                      <span key={tag} className={styles.tag}>{tag}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section 4: Platform Architecture, Governance & Customization */}
        <section className="section bg-subtle">
          <div className="container">
            <div className="section-header centered">
              <span className="section-label">Platform Infrastructure</span>
              <h2 className="section-title">Ingestion, Governance &amp; Administration</h2>
              <p className="section-subtitle">
                Robust foundation providing authenticated telemetry, tenant isolation, physical disk diagnostics, and customizable UI density.
              </p>
            </div>
            <div className={styles.featuresGrid}>
              {PLATFORM_FEATURES.map(({ icon, category, title, desc, tags }) => (
                <div key={title} className={styles.featureCard}>
                  <div className={styles.featureCardTop}>
                    <div className={styles.featureIcon}>{icon}</div>
                    <span className={styles.featureCategory}>{category}</span>
                  </div>
                  <h3 className={styles.featureTitle}>{title}</h3>
                  <p className={styles.featureDesc}>{desc}</p>
                  <div className={styles.featureTags}>
                    {tags.map((tag) => (
                      <span key={tag} className={styles.tag}>{tag}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Call to action */}
        <section className="section-sm">
          <div className="container" style={{ textAlign: 'center' }}>
            <h2 className="section-title">Ready to experience facility intelligence?</h2>
            <p className="section-subtitle" style={{ margin: '1rem auto 2rem' }}>
              Sign in to the GreenNexa operational dashboard to monitor your facility telemetry, review active anomalies, and test the Gemini 2.5 Flash assistant.
            </p>
            <Link href="/login" className="btn btn-primary btn-lg">
              Access Operational Dashboard
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
