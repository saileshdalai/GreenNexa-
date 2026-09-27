import type { Metadata } from 'next';
import Link from 'next/link';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import styles from './page.module.css';

export const metadata: Metadata = {
  title: 'Pricing',
  description:
    'GreenNexa pricing plans — Free, Pro and Enterprise. Demo / Planned pricing for AI-powered sustainable facility intelligence.',
};

const PLANS = [
  {
    name: 'Free',
    price: '₹0',
    period: 'forever',
    desc: 'Get started with basic facility monitoring using synthetic demo data.',
    features: [
      'Basic dashboard',
      'Synthetic data mode',
      'Basic analytics',
      'Up to 1 organisation',
      'Community support',
    ],
    cta: 'Get Started',
    href: '/login',
    highlight: false,
  },
  {
    name: 'Pro',
    price: '₹4,999',
    period: 'per month',
    desc: 'Advanced analytics and AI for growing facilities ready to connect real sensors.',
    features: [
      'Everything in Free',
      'Advanced analytics',
      'AI anomaly detection',
      'AI forecasting',
      'IoT device support',
      'Advanced reports',
      'WhatsApp alert option',
      'Priority support',
    ],
    cta: 'Get Pro',
    href: '/login',
    highlight: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: 'contact us',
    desc: 'For large organisations with multiple facilities and advanced access requirements.',
    features: [
      'Everything in Pro',
      'Multiple organisations',
      'Multiple facilities',
      'Advanced RBAC',
      'Audit logs',
      'Advanced reporting',
      'Custom sensor configuration',
      'Dedicated support',
      'SLA available',
    ],
    cta: 'Contact Sales',
    href: '/contact',
    highlight: false,
  },
];

export default function PricingPage() {
  return (
    <>
      <Header />
      <main>
        <section className={styles.pageHero}>
          <div className="container">
            <span className="section-label">💳 Pricing</span>
            <h1 className="section-title">Simple, transparent pricing</h1>
            <p className="section-subtitle">
              Choose the plan that fits your facility. All plans include the core GreenNexa platform.
            </p>
            {/* Important demo notice */}
            <div className={styles.demoNotice}>
              📋 <strong>Demo / Planned Pricing</strong> — These are illustrative tiers for demonstration purposes.
              No real payment processing is active. Contact us to discuss actual pricing.
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className={styles.plansGrid}>
              {PLANS.map(({ name, price, period, desc, features, cta, href, highlight }) => (
                <div key={name} className={`${styles.planCard} ${highlight ? styles.planHighlight : ''}`}>
                  {highlight && <div className={styles.popularBadge}>Most Popular</div>}
                  <div className={styles.planHeader}>
                    <h2 className={styles.planName}>{name}</h2>
                    <div className={styles.planPrice}>
                      <span className={styles.priceValue}>{price}</span>
                      <span className={styles.pricePeriod}>{period}</span>
                    </div>
                    <p className={styles.planDesc}>{desc}</p>
                  </div>
                  <ul className={styles.featureList}>
                    {features.map((f) => (
                      <li key={f} className={styles.featureItem}>
                        <span className={styles.checkIcon}>✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Link href={href} className={`btn ${highlight ? 'btn-primary' : 'btn-outline'} ${styles.planCta}`}>
                    {cta}
                  </Link>
                </div>
              ))}
            </div>

            <div className={styles.disclaimer}>
              <strong>Note:</strong> GreenNexa AI insights, forecasts and sustainability scores are decision-support
              tools — not official certifications or guaranteed predictions. All pricing shown is illustrative.
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
