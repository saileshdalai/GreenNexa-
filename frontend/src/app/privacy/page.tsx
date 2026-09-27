import type { Metadata } from 'next';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import styles from './page.module.css';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'GreenNexa Privacy Policy — how we collect, use, store and protect your data.',
};

const LAST_UPDATED = 'September 2026';

export default function PrivacyPage() {
  return (
    <>
      <Header />
      <main>
        <section className={styles.pageHero}>
          <div className="container">
            <span className="section-label">🔒 Legal</span>
            <h1 className="section-title">Privacy Policy</h1>
            <p className={styles.lastUpdated}>Last updated: {LAST_UPDATED}</p>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className={styles.legalDoc}>

              <div className={styles.intro}>
                This Privacy Policy explains how GreenNexa collects, uses, stores and protects information
                when you use the GreenNexa platform. By using GreenNexa, you agree to the practices described
                in this policy.
              </div>

              <Section title="1. Information We Collect">
                <SubSection title="Account Information">
                  When an organisation administrator account is created, we collect: organisation name,
                  organisation ID, administrator name, user ID, email address, phone number and a securely
                  hashed password. Passwords are never stored in plain text.
                </SubSection>
                <SubSection title="Organisation Information">
                  We collect organisation name, organisation type, location and operational status to
                  configure and scope the platform correctly.
                </SubSection>
                <SubSection title="Facility Information">
                  We store building, floor and zone information used to organise sensor data and generate reports.
                </SubSection>
                <SubSection title="Sensor and IoT Data">
                  We collect sensor readings including energy consumption, water flow, waste metrics,
                  temperature, humidity, CO₂ levels and other configured environmental metrics. Each
                  reading is tagged with its source (IoT or Synthetic), device ID, organisation ID and timestamp.
                  We do not collect personally identifiable information through sensors.
                </SubSection>
              </Section>

              <Section title="2. How We Use Your Data">
                <ul className={styles.list}>
                  <li>To authenticate and authorise platform access</li>
                  <li>To display facility metrics on the dashboard</li>
                  <li>To run AI/ML analysis, anomaly detection and forecasting</li>
                  <li>To generate sustainability reports</li>
                  <li>To send alerts and notifications to authorised administrators</li>
                  <li>To maintain audit logs for security and compliance</li>
                  <li>To improve platform performance and reliability</li>
                </ul>
              </Section>

              <Section title="3. Data Storage">
                <p>
                  All data is stored in a PostgreSQL database. Sensor readings, user accounts, organisation
                  data and AI results are stored with organisation-level separation. No administrator can
                  access data belonging to another organisation.
                </p>
              </Section>

              <Section title="4. Security">
                <ul className={styles.list}>
                  <li>Passwords are hashed using a strong algorithm (Argon2id). Plaintext passwords are never stored.</li>
                  <li>All API communication uses HTTPS.</li>
                  <li>IoT devices use device-specific credentials — not administrator passwords.</li>
                  <li>Role-Based Access Control (RBAC) is enforced at the backend for every request.</li>
                  <li>Organisation-level data isolation is enforced server-side.</li>
                  <li>OTPs for password reset are time-limited, single-use and rate-limited.</li>
                </ul>
                <p style={{ marginTop: '0.75rem' }}>
                  We only claim the security features that are actually implemented in the platform.
                </p>
              </Section>

              <Section title="5. Access Control">
                <p>
                  GreenNexa uses three roles: Super Admin, Admin and Operations User. Super Admins manage
                  the platform. Admins manage their assigned organisation only. Operations Users have
                  restricted, permission-based access. Every data request is validated server-side against
                  the requesting user&apos;s role and organisation.
                </p>
              </Section>

              <Section title="6. Data Retention">
                <p>
                  Sensor data and operational records are retained for the duration of your active
                  subscription. Historical sensor data is preserved even if individual sensors are
                  deactivated — only explicit deletion requests remove data.
                </p>
              </Section>

              <Section title="7. Deletion">
                <p>
                  Administrators may request deletion of their organisation&apos;s data by contacting GreenNexa.
                  Super Admins can deactivate organisations through the platform. Data deletion is irreversible.
                </p>
              </Section>

              <Section title="8. Third-Party Services">
                <p>
                  GreenNexa may integrate with WhatsApp (for message-box pre-fill notifications only — no
                  automatic sending), SMS providers (for OTP verification) and mapping services. No sensor
                  data or personally identifiable information is shared with third parties for advertising purposes.
                </p>
              </Section>

              <Section title="9. Synthetic Data">
                <p>
                  If your organisation uses Synthetic Data mode, the data is generated by GreenNexa&apos;s
                  simulator for demonstration purposes. It is clearly labelled as synthetic and does not
                  represent real facility conditions.
                </p>
              </Section>

              <Section title="10. Contact">
                <p>
                  For privacy-related questions, data requests or deletion requests, please contact GreenNexa
                  through the Contact page. Contact details are configured by the project owner.
                </p>
              </Section>

            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className={styles.section}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      <div className={styles.sectionBody}>{children}</div>
    </div>
  );
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className={styles.subSection}>
      <h3 className={styles.subTitle}>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
