'use client';

import { useState } from 'react';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import styles from './page.module.css';

export default function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', message: '' });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.message.trim()) {
      setError('Please fill in all fields.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError('Please enter a valid email address.');
      return;
    }
    setSubmitted(true);
  };

  return (
    <>
      <Header />
      <main>
        <section className={styles.pageHero}>
          <div className="container">
            <span className="section-label">📬 Contact</span>
            <h1 className="section-title">Get in touch</h1>
            <p className="section-subtitle">
              Have a question about GreenNexa? We would love to hear from you.
            </p>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <div className={styles.contactGrid}>

              {/* Contact info */}
              <div className={styles.contactInfo}>
                <h2 className={styles.infoTitle}>Contact Information</h2>
                <div className={styles.infoItems}>
                  <div className={styles.infoItem}>
                    <span className={styles.infoIcon}>📧</span>
                    <div>
                      <strong>Email</strong>
                      <p>Contact details will be configured by the project owner.</p>
                    </div>
                  </div>
                  <div className={styles.infoItem}>
                    <span className={styles.infoIcon}>📱</span>
                    <div>
                      <strong>WhatsApp / Phone</strong>
                      <p>Contact details will be configured by the project owner.</p>
                    </div>
                  </div>
                  <div className={styles.infoItem}>
                    <span className={styles.infoIcon}>🌐</span>
                    <div>
                      <strong>Platform</strong>
                      <p>greennexa.app</p>
                    </div>
                  </div>
                </div>
                <div className={styles.infoNote}>
                  Contact details are intentionally left unconfigured until the project owner
                  provides real contact information. Placeholder details are not displayed.
                </div>
              </div>

              {/* Contact form */}
              <div className={styles.formWrap}>
                {submitted ? (
                  <div className={styles.successBox}>
                    <span className={styles.successIcon}>✅</span>
                    <h3>Message received!</h3>
                    <p>
                      Thank you for contacting GreenNexa. We will get back to you soon.
                    </p>
                    <button
                      className="btn btn-outline"
                      onClick={() => { setSubmitted(false); setForm({ name: '', email: '', message: '' }); }}
                    >
                      Send another message
                    </button>
                  </div>
                ) : (
                  <form className={styles.form} onSubmit={handleSubmit} noValidate>
                    <h2 className={styles.formTitle}>Send us a message</h2>

                    <div className="form-group">
                      <label htmlFor="contact-name" className="form-label">Full Name</label>
                      <input
                        id="contact-name"
                        name="name"
                        type="text"
                        className="form-input"
                        placeholder="Your name"
                        value={form.name}
                        onChange={handleChange}
                        autoComplete="name"
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="contact-email" className="form-label">Email Address</label>
                      <input
                        id="contact-email"
                        name="email"
                        type="email"
                        className="form-input"
                        placeholder="your@email.com"
                        value={form.email}
                        onChange={handleChange}
                        autoComplete="email"
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="contact-message" className="form-label">Message</label>
                      <textarea
                        id="contact-message"
                        name="message"
                        className="form-input"
                        placeholder="How can we help you?"
                        value={form.message}
                        onChange={handleChange}
                        rows={5}
                      />
                    </div>

                    {error && <div className={styles.errorMsg}>{error}</div>}

                    <button id="contact-submit" type="submit" className="btn btn-primary" style={{ width: '100%' }}>
                      Send Message
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
