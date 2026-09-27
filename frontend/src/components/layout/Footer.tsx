import Link from 'next/link';
import Image from 'next/image';
import styles from './Footer.module.css';

const QUICK_LINKS = [
  { href: '/',             label: 'Home' },
  { href: '/about',        label: 'About' },
  { href: '/features',     label: 'Features' },
  { href: '/how-it-works', label: 'How It Works' },
  { href: '/pricing',      label: 'Pricing' },
  { href: '/contact',      label: 'Contact' },
];

const LEGAL_LINKS = [
  { href: '/privacy', label: 'Privacy Policy' },
  { href: '/terms',   label: 'Terms & Conditions' },
];

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className={styles.footer}>
      <div className="container">
        <div className={styles.grid}>

          {/* Brand column */}
          <div className={styles.brand}>
            <Link href="/" aria-label="GreenNexa home">
              <Image
                src="/branding/greennexa-logo.png"
                alt="GreenNexa"
                width={140}
                height={46}
                style={{ objectFit: 'contain', width: 'auto', height: '40px', filter: 'brightness(0) invert(1)' }}
              />
            </Link>
            <p className={styles.brandDesc}>
              AI-Powered Sustainable Facility Intelligence. Monitor, predict and
              optimize your facility operations with intelligent data analytics.
            </p>
            <div className={styles.badges}>
              <span className={styles.badge}>🌿 Sustainable</span>
              <span className={styles.badge}>🤖 AI-Powered</span>
              <span className={styles.badge}>📡 IoT Ready</span>
            </div>
          </div>

          {/* Quick links */}
          <div className={styles.linkCol}>
            <h4 className={styles.colTitle}>Platform</h4>
            <ul className={styles.linkList}>
              {QUICK_LINKS.map(({ href, label }) => (
                <li key={href}>
                  <Link href={href} className={styles.link}>{label}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div className={styles.linkCol}>
            <h4 className={styles.colTitle}>Legal</h4>
            <ul className={styles.linkList}>
              {LEGAL_LINKS.map(({ href, label }) => (
                <li key={href}>
                  <Link href={href} className={styles.link}>{label}</Link>
                </li>
              ))}
            </ul>
            <div className={styles.loginCta}>
              <h4 className={styles.colTitle} style={{ marginTop: '1.5rem' }}>Access</h4>
              <Link href="/login" className="btn btn-outline" style={{ color: '#bbf7d0', borderColor: '#bbf7d0', marginTop: '8px' }}>
                Login to Dashboard
              </Link>
            </div>
          </div>
        </div>

        <div className={styles.bottom}>
          <p className={styles.copy}>
            &copy; {year} GreenNexa. All rights reserved.
          </p>
          <p className={styles.disclaimer}>
            GreenNexa sustainability scores are calculated estimates, not official certifications.
          </p>
        </div>
      </div>
    </footer>
  );
}
