import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import styles from './page.module.css';

import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';

export const metadata: Metadata = {
  title: 'GreenNexa — AI-Powered Sustainable Facility Intelligence',
  description:
    'Monitor, predict and optimize your facility with GreenNexa — combining AI, IoT and real-time analytics for energy, water, waste and environmental intelligence.',
};

const FEATURES = [
  { icon: '⚡', title: 'Energy Intelligence', desc: 'Monitor and forecast electricity consumption with AI-powered insights.' },
  { icon: '💧', title: 'Water Intelligence', desc: 'Track water consumption trends and detect unusual usage patterns.' },
  { icon: '♻️', title: 'Waste Intelligence', desc: 'Measure and manage waste generation across your facility.' },
  { icon: '🌡️', title: 'Environmental', desc: 'Monitor temperature, humidity, CO₂ and air quality in real time.' },
  { icon: '🤖', title: 'AI Forecasting', desc: 'Predict future trends from historical sensor data.' },
  { icon: '🚨', title: 'Anomaly Detection', desc: 'Identify unusual readings automatically and alert administrators.' },
];

const FLOW_STEPS = [
  { step: '01', label: 'Collect', icon: '📡', desc: 'IoT sensors or synthetic data' },
  { step: '02', label: 'Validate', icon: '✅', desc: 'Data integrity & range checks' },
  { step: '03', label: 'Analyse', icon: '🧠', desc: 'AI/ML processing pipeline' },
  { step: '04', label: 'Detect', icon: '🔍', desc: 'Anomaly detection engine' },
  { step: '05', label: 'Alert', icon: '🚨', desc: 'Smart notifications to admins' },
  { step: '06', label: 'Act', icon: '📊', desc: 'Dashboard insights & reports' },
];

const TRUST_STATS = [
  { value: '3 min', label: 'Data Update Cycle' },
  { value: '4 Modules', label: 'Intelligence Domains' },
  { value: 'RBAC', label: 'Role-Based Access' },
  { value: 'AI+IoT', label: 'Powered By' },
];

export default function HomePage() {
  return (
    <>
      <Header />
      <main>
      {/* ── Hero ─────────────────────────────────────────── */}
      <section className={styles.hero}>
        <div className={`container ${styles.heroInner}`}>
          <div className={styles.heroContent}>
            <div className={styles.heroBadge}>
              🌿 Sustainable Facility Intelligence
            </div>
            <h1 className={styles.heroTitle}>
              AI-Powered<br />
              <span className={styles.heroAccent}>Sustainable Facility</span><br />
              Intelligence
            </h1>
            <p className={styles.heroSub}>
              <strong>Monitor. Predict. Optimize.</strong>
            </p>
            <p className={styles.heroDesc}>
              GreenNexa combines AI, IoT and advanced analytics to give facility managers
              real-time visibility into energy, water, waste and environmental performance —
              with intelligent anomaly detection and actionable recommendations.
            </p>
            <div className={styles.heroCta}>
              <Link href="/features" className="btn btn-primary btn-lg">
                Explore Platform
              </Link>
              <Link href="/login" className="btn btn-outline btn-lg">
                Login
              </Link>
            </div>
            <div className={styles.trustRow}>
              {TRUST_STATS.map(({ value, label }) => (
                <div key={label} className={styles.trustStat}>
                  <span className={styles.trustValue}>{value}</span>
                  <span className={styles.trustLabel}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Hero visual panel */}
          <div className={styles.heroVisual}>
            <div className={styles.dashCard}>
              <div className={styles.dashHeader}>
                <span className={styles.dashDot} style={{ background: '#ef4444' }} />
                <span className={styles.dashDot} style={{ background: '#f59e0b' }} />
                <span className={styles.dashDot} style={{ background: '#22c55e' }} />
                <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#6b9b7f' }}>GreenNexa Dashboard</span>
              </div>
              <div className={styles.dashBody}>
                <div className={styles.kpiRow}>
                  {[
                    { label: 'Energy', value: '1,248 kWh', change: '−4.2%', ok: true },
                    { label: 'Water',  value: '482 L',     change: '+1.1%', ok: true },
                    { label: 'Score',  value: '82/100',    change: 'Good',  ok: true },
                    { label: 'Alerts', value: '2 Open',    change: 'HIGH',  ok: false },
                  ].map(({ label, value, change, ok }) => (
                    <div key={label} className={styles.kpiCard}>
                      <span className={styles.kpiLabel}>{label}</span>
                      <span className={styles.kpiValue}>{value}</span>
                      <span className={styles.kpiChange} style={{ color: ok ? '#22c55e' : '#ef4444' }}>{change}</span>
                    </div>
                  ))}
                </div>
                {/* Fake bar chart */}
                <div className={styles.fakeChart}>
                  <div className={styles.chartLabel}>Energy — 7 Day Trend</div>
                  <div className={styles.chartBars}>
                    {[65, 72, 68, 80, 74, 88, 76].map((h, i) => (
                      <div key={i} className={styles.chartBarWrap}>
                        <div className={styles.chartBar} style={{ height: `${h}%` }} />
                        <span className={styles.chartBarDay}>{['M','T','W','T','F','S','S'][i]}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className={styles.aiInsight}>
                  <span className={styles.aiTag}>🤖 AI Insight</span>
                  <span className={styles.aiText}>Energy usage is 8% above weekly average. Check HVAC schedule.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features Strip ───────────────────────────────── */}
      <section className={`section bg-subtle`}>
        <div className="container">
          <div className="section-header centered">
            <span className="section-label">✦ Platform Capabilities</span>
            <h2 className="section-title">Everything your facility needs</h2>
            <p className="section-subtitle">
              Six intelligence domains working together to give you a complete picture
              of your facility's operational and environmental performance.
            </p>
          </div>
          <div className="grid-3">
            {FEATURES.map(({ icon, title, desc }) => (
              <div key={title} className="card">
                <div className="card-icon" style={{ fontSize: '1.5rem' }}>{icon}</div>
                <h3 className="card-title">{title}</h3>
                <p className="card-desc">{desc}</p>
              </div>
            ))}
          </div>
          <div style={{ textAlign: 'center', marginTop: '2.5rem' }}>
            <Link href="/features" className="btn btn-outline">
              View All Features →
            </Link>
          </div>
        </div>
      </section>

      {/* ── How It Works ─────────────────────────────────── */}
      <section className="section">
        <div className="container">
          <div className="section-header centered">
            <span className="section-label">⚙️ The Process</span>
            <h2 className="section-title">From raw data to actionable intelligence</h2>
            <p className="section-subtitle">
              GreenNexa processes sensor readings every 3 minutes through a validated
              AI pipeline — turning noise into decisions.
            </p>
          </div>
          <div className={styles.flowGrid}>
            {FLOW_STEPS.map(({ step, label, icon, desc }, idx) => (
              <div key={step} className={styles.flowItem}>
                <div className={styles.flowStep}>
                  <div className={styles.flowNum}>{step}</div>
                  <div className={styles.flowIcon}>{icon}</div>
                </div>
                <div className={styles.flowText}>
                  <strong>{label}</strong>
                  <span>{desc}</span>
                </div>
                {idx < FLOW_STEPS.length - 1 && (
                  <div className={styles.flowConnector} aria-hidden="true">→</div>
                )}
              </div>
            ))}
          </div>
          <div style={{ textAlign: 'center', marginTop: '2.5rem' }}>
            <Link href="/how-it-works" className="btn btn-primary">
              See Detailed Flow →
            </Link>
          </div>
        </div>
      </section>

      {/* ── CTA Banner ───────────────────────────────────── */}
      <section className={styles.ctaBanner}>
        <div className="container">
          <div className={styles.ctaInner}>
            <div>
              <h2 className={styles.ctaTitle}>Ready to optimize your facility?</h2>
              <p className={styles.ctaSub}>
                Join GreenNexa and start making data-driven sustainability decisions today.
              </p>
            </div>
            <div className={styles.ctaButtons}>
              <Link href="/login" className="btn btn-accent btn-lg">
                Get Started
              </Link>
              <Link href="/pricing" className="btn btn-outline btn-lg" style={{ color: '#fff', borderColor: 'rgba(255,255,255,0.5)' }}>
                View Pricing
              </Link>
            </div>
          </div>
        </div>
      </section>
      </main>
      <Footer />
    </>
  );
}
