'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { api } from '@/lib/api';
import styles from './page.module.css';

export default function LoginPage() {
  const [organisationType, setOrganisationType] = useState<'GOVERNMENT' | 'PRIVATE'>('GOVERNMENT');
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword]               = useState('');
  const [showPassword, setShowPassword]       = useState(false);
  const [error, setError]                     = useState('');
  const [loading, setLoading]                 = useState(false);

  // Forgot Password Flow States
  const [isForgotMode, setIsForgotMode]       = useState(false);
  const [forgotStep, setForgotStep]           = useState<1 | 2 | 3 | 4>(1);
  const [forgotIdentifier, setForgotIdentifier] = useState('');
  const [sessionId, setSessionId]             = useState('');
  const [maskedPhone, setMaskedPhone]         = useState('');
  const [otpCode, setOtpCode]                 = useState('');
  const [newPassword, setNewPassword]         = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [forgotError, setForgotError]         = useState('');
  const [forgotSuccess, setForgotSuccess]     = useState('');
  const [forgotLoading, setForgotLoading]     = useState(false);
  const [cooldown, setCooldown]               = useState(0);
  const [resetToken, setResetToken]           = useState('');

  const { login } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();

  // Cooldown countdown timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (cooldown > 0) {
      interval = setInterval(() => {
        setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [cooldown]);

  const handleAuth = async (userVal: string, passVal: string) => {
    setError('');
    setLoading(true);
    try {
      const user = await login(userVal.trim(), passVal, organisationType);
      showToast(`Welcome back, ${user.full_name || user.email}!`, "success");
      if (user.role === "SUPER_ADMIN") {
        router.push('/super-admin');
      } else {
        router.push('/dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Invalid User ID/Email or password.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail.trim()) {
      setError('User ID or Email is required.');
      return;
    }
    if (!password.trim()) {
      setError('Password is required.');
      return;
    }
    handleAuth(usernameOrEmail, password);
  };

  // Step 1: Request OTP
  const handleRequestOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const id = forgotIdentifier.trim();
    if (!id) {
      setForgotError('Please enter your User ID or Email.');
      return;
    }
    setForgotError('');
    setForgotLoading(true);
    try {
      const res = await api.post<{
        status: string;
        message: string;
        masked_phone?: string;
        session_id?: string;
        cooldown_seconds?: number;
      }>('/api/v1/auth/forgot-password/request', { identifier: id });

      setSessionId(res.session_id || '');
      setMaskedPhone(res.masked_phone || '');
      setCooldown(res.cooldown_seconds || 60);
      setForgotSuccess(res.message);
      setForgotStep(2);
      showToast('OTP generated and dispatched to registered mobile number.', 'info');
    } catch (err: any) {
      setForgotError(err.message || 'Failed to request OTP. Please try again.');
    } finally {
      setForgotLoading(false);
    }
  };

  // Resend OTP
  const handleResendOtp = async () => {
    if (cooldown > 0) return;
    setForgotError('');
    setForgotLoading(true);
    try {
      const res = await api.post<{
        status: string;
        message: string;
        masked_phone?: string;
        session_id?: string;
        cooldown_seconds?: number;
      }>('/api/v1/auth/forgot-password/request', { identifier: forgotIdentifier.trim() });

      setSessionId(res.session_id || '');
      setCooldown(res.cooldown_seconds || 60);
      setForgotSuccess('A new OTP has been sent to your registered mobile number.');
      showToast('New OTP sent successfully.', 'success');
    } catch (err: any) {
      setForgotError(err.message || 'Failed to resend OTP.');
    } finally {
      setForgotLoading(false);
    }
  };

  // Step 2: Verify OTP
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    const otp = otpCode.trim();
    if (!otp) {
      setForgotError('Please enter the 6-digit OTP code.');
      return;
    }
    if (otp.length < 4) {
      setForgotError('OTP code must be at least 4 digits.');
      return;
    }
    setForgotError('');
    setForgotLoading(true);
    try {
      const res = await api.post<{
        status: string;
        message: string;
        reset_token: string;
      }>('/api/v1/auth/forgot-password/verify-otp', {
        session_id: sessionId,
        otp: otp,
      });

      setResetToken(res.reset_token);
      setForgotError('');
      setForgotSuccess('OTP verified successfully.');
      setForgotStep(3);
    } catch (err: any) {
      setForgotError(err.message || 'Incorrect OTP code. Please try again.');
    } finally {
      setForgotLoading(false);
    }
  };

  // Step 3: Reset Password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPassword) {
      setForgotError('New password is required.');
      return;
    }
    if (newPassword.length < 6) {
      setForgotError('Password must be at least 6 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setForgotError('Passwords do not match.');
      return;
    }

    setForgotError('');
    setForgotLoading(true);
    try {
      await api.post<{
        status: string;
        message: string;
      }>('/api/v1/auth/forgot-password/reset-password', {
        reset_token: resetToken,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      setForgotStep(4);
      showToast('Password reset successful!', 'success');
    } catch (err: any) {
      setForgotError(err.message || 'Failed to reset password. Session may have expired.');
    } finally {
      setForgotLoading(false);
    }
  };

  // Return to Login from forgot flow
  const handleReturnToLogin = () => {
    setIsForgotMode(false);
    setForgotStep(1);
    setForgotError('');
    setForgotSuccess('');
    setOtpCode('');
    setNewPassword('');
    setConfirmPassword('');
    if (forgotIdentifier) {
      setUsernameOrEmail(forgotIdentifier);
    }
  };

  return (
    <div className={styles.loginPage}>
      <div className={styles.loginCard}>

        {/* Logo & Theme Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-8)' }}>
          <Link href="/">
            <Image
              src="/branding/greennexa-logo.png"
              alt="GreenNexa"
              width={180}
              height={60}
              priority
              style={{ objectFit: 'contain', width: 'auto', height: '48px' }}
            />
          </Link>
          <ThemeToggle />
        </div>

        {/* FORGOT PASSWORD FLOW */}
        {isForgotMode ? (
          <div className={styles.form}>
            {/* STEP 1: Enter User ID / Email */}
            {forgotStep === 1 && (
              <form onSubmit={handleRequestOtp} noValidate>
                <h1 className={styles.formTitle}>Forgot Password</h1>
                <p style={{ fontSize: '13px', color: 'var(--clr-text-secondary)', marginBottom: '20px', lineHeight: '1.5' }}>
                  Enter your registered User ID or Email. We will send a secure One-Time Password (OTP) to your registered mobile number.
                </p>

                <div className="form-group" style={{ marginBottom: '18px' }}>
                  <label htmlFor="forgot-identifier" className="form-label" style={{ fontWeight: 600, fontSize: '13px' }}>
                    User ID / Email
                  </label>
                  <input
                    id="forgot-identifier"
                    type="text"
                    className="form-input"
                    placeholder="e.g. sailesh@gmail.com or BERMHAPUR_NAC_ADMIN"
                    value={forgotIdentifier}
                    onChange={(e) => { setForgotIdentifier(e.target.value); setForgotError(''); }}
                    autoComplete="username"
                    required
                  />
                </div>

                {forgotError && (
                  <div className={styles.errorMsg} id="forgot-error" role="alert" style={{ marginBottom: '16px' }}>
                    {forgotError}
                  </div>
                )}

                <button
                  id="btn-send-otp"
                  type="submit"
                  className={`btn btn-primary ${styles.submitBtn}`}
                  disabled={forgotLoading}
                  style={{ width: '100%', marginBottom: '14px' }}
                >
                  {forgotLoading ? 'Sending OTP…' : 'Send OTP'}
                </button>

                <button
                  type="button"
                  id="btn-back-to-login"
                  onClick={handleReturnToLogin}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--clr-text-secondary)',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'block',
                    width: '100%',
                    textAlign: 'center',
                    padding: '8px',
                  }}
                >
                  ← Back to Sign In
                </button>
              </form>
            )}

            {/* STEP 2: Enter OTP */}
            {forgotStep === 2 && (
              <form onSubmit={handleVerifyOtp} noValidate>
                <h1 className={styles.formTitle}>OTP Verification</h1>
                <p style={{ fontSize: '13px', color: 'var(--clr-text-secondary)', marginBottom: '20px', lineHeight: '1.5' }}>
                  Enter the 6-digit OTP code sent to your registered phone number{' '}
                  {maskedPhone ? <strong style={{ color: '#10b981' }}>({maskedPhone})</strong> : ''}.
                </p>

                <div className="form-group" style={{ marginBottom: '18px' }}>
                  <label htmlFor="forgot-otp" className="form-label" style={{ fontWeight: 600, fontSize: '13px' }}>
                    Enter 6-Digit OTP
                  </label>
                  <input
                    id="forgot-otp"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    className="form-input"
                    placeholder="• • • • • •"
                    value={otpCode}
                    onChange={(e) => { setOtpCode(e.target.value.replace(/\D/g, '')); setForgotError(''); }}
                    style={{
                      letterSpacing: '8px',
                      fontSize: '20px',
                      fontWeight: 700,
                      textAlign: 'center',
                    }}
                    autoComplete="one-time-code"
                    required
                  />
                </div>

                {/* Resend OTP with Countdown */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', fontSize: '13px' }}>
                  <span style={{ color: 'var(--clr-text-secondary)' }}>Didn't receive code?</span>
                  {cooldown > 0 ? (
                    <span style={{ color: 'var(--clr-text-muted)', fontWeight: 600, fontFamily: 'monospace' }}>
                      Resend in {cooldown}s
                    </span>
                  ) : (
                    <button
                      type="button"
                      id="btn-resend-otp"
                      onClick={handleResendOtp}
                      disabled={forgotLoading}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--clr-primary, #10b981)',
                        fontWeight: 700,
                        cursor: 'pointer',
                        padding: 0,
                        textDecoration: 'underline',
                      }}
                    >
                      Resend OTP
                    </button>
                  )}
                </div>

                {forgotError && (
                  <div className={styles.errorMsg} id="forgot-error" role="alert" style={{ marginBottom: '16px' }}>
                    {forgotError}
                  </div>
                )}

                <button
                  id="btn-verify-otp"
                  type="submit"
                  className={`btn btn-primary ${styles.submitBtn}`}
                  disabled={forgotLoading || otpCode.length < 4}
                  style={{ width: '100%', marginBottom: '14px' }}
                >
                  {forgotLoading ? 'Verifying OTP…' : 'Verify OTP'}
                </button>

                <button
                  type="button"
                  onClick={() => { setForgotStep(1); setForgotError(''); }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--clr-text-secondary)',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'block',
                    width: '100%',
                    textAlign: 'center',
                    padding: '8px',
                  }}
                >
                  ← Change Identifier
                </button>
              </form>
            )}

            {/* STEP 3: Set New Password */}
            {forgotStep === 3 && (
              <form onSubmit={handleResetPassword} noValidate>
                <h1 className={styles.formTitle}>Set New Password</h1>
                <p style={{ fontSize: '13px', color: 'var(--clr-text-secondary)', marginBottom: '20px', lineHeight: '1.5' }}>
                  Please create a strong new password for your GreenNexa account (minimum 6 characters).
                </p>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label htmlFor="forgot-new-password" className="form-label" style={{ fontWeight: 600, fontSize: '13px' }}>
                    New Password
                  </label>
                  <div className={styles.passwordWrap}>
                    <input
                      id="forgot-new-password"
                      type={showNewPassword ? 'text' : 'password'}
                      className="form-input"
                      placeholder="Enter new password (min 6 chars)"
                      value={newPassword}
                      onChange={(e) => { setNewPassword(e.target.value); setForgotError(''); }}
                      required
                    />
                    <button
                      type="button"
                      className={styles.showPasswordBtn}
                      onClick={() => setShowNewPassword((v) => !v)}
                      aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                    >
                      {showNewPassword ? '🙈' : '👁️'}
                    </button>
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: '20px' }}>
                  <label htmlFor="forgot-confirm-password" className="form-label" style={{ fontWeight: 600, fontSize: '13px' }}>
                    Confirm New Password
                  </label>
                  <input
                    id="forgot-confirm-password"
                    type={showNewPassword ? 'text' : 'password'}
                    className="form-input"
                    placeholder="Re-enter new password"
                    value={confirmPassword}
                    onChange={(e) => { setConfirmPassword(e.target.value); setForgotError(''); }}
                    required
                  />
                </div>

                {forgotError && (
                  <div className={styles.errorMsg} id="forgot-error" role="alert" style={{ marginBottom: '16px' }}>
                    {forgotError}
                  </div>
                )}

                <button
                  id="btn-reset-password"
                  type="submit"
                  className={`btn btn-primary ${styles.submitBtn}`}
                  disabled={forgotLoading}
                  style={{ width: '100%', marginBottom: '14px' }}
                >
                  {forgotLoading ? 'Updating Password…' : 'Update Password'}
                </button>

                <button
                  type="button"
                  onClick={handleReturnToLogin}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--clr-text-secondary)',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'block',
                    width: '100%',
                    textAlign: 'center',
                    padding: '8px',
                  }}
                >
                  ← Cancel and Return to Sign In
                </button>
              </form>
            )}

            {/* STEP 4: Success confirmation */}
            {forgotStep === 4 && (
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <div style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  background: 'rgba(16, 185, 129, 0.15)',
                  color: '#10b981',
                  fontSize: '28px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 18px',
                  border: '2px solid #10b981'
                }}>
                  ✓
                </div>
                <h1 className={styles.formTitle} style={{ marginBottom: '8px' }}>Password Updated!</h1>
                <p style={{ fontSize: '14px', color: 'var(--clr-text-secondary)', marginBottom: '24px', lineHeight: '1.5' }}>
                  Your password has been reset successfully. You can now sign in with your new password.
                </p>

                <button
                  id="btn-return-login"
                  type="button"
                  className={`btn btn-primary ${styles.submitBtn}`}
                  onClick={handleReturnToLogin}
                  style={{ width: '100%' }}
                >
                  Return to Sign In
                </button>
              </div>
            )}
          </div>
        ) : (
          /* STANDARD PRODUCTION LOGIN FORM */
          <form onSubmit={handleSubmit} className={styles.form} noValidate>
            <h1 className={styles.formTitle}>Sign In</h1>
            <p style={{ fontSize: '13px', color: 'var(--clr-text-secondary)', marginBottom: '20px', textAlign: 'center' }}>
              Enter your credentials to access your GreenNexa account
            </p>

            {/* Choose Organisation Type */}
            <div className="form-group" style={{ marginBottom: '18px' }}>
              <label className="form-label" style={{ fontWeight: 600, fontSize: '13px', display: 'block', marginBottom: '8px' }}>
                Choose Organisation Type
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <button
                  type="button"
                  id="login-type-government"
                  style={{
                    padding: '11px 14px',
                    borderRadius: '8px',
                    border: organisationType === 'GOVERNMENT' ? '2px solid #10b981' : '1px solid var(--clr-border, #334155)',
                    background: organisationType === 'GOVERNMENT' ? 'rgba(16, 185, 129, 0.12)' : 'var(--clr-surface, #1e293b)',
                    color: organisationType === 'GOVERNMENT' ? '#10b981' : 'var(--clr-text-secondary, #94a3b8)',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.15s ease'
                  }}
                  onClick={() => { setOrganisationType('GOVERNMENT'); setError(''); }}
                >
                  <span>🏛️</span> Government
                </button>
                <button
                  type="button"
                  id="login-type-private"
                  style={{
                    padding: '11px 14px',
                    borderRadius: '8px',
                    border: organisationType === 'PRIVATE' ? '2px solid #10b981' : '1px solid var(--clr-border, #334155)',
                    background: organisationType === 'PRIVATE' ? 'rgba(16, 185, 129, 0.12)' : 'var(--clr-surface, #1e293b)',
                    color: organisationType === 'PRIVATE' ? '#10b981' : 'var(--clr-text-secondary, #94a3b8)',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    transition: 'all 0.15s ease'
                  }}
                  onClick={() => { setOrganisationType('PRIVATE'); setError(''); }}
                >
                  <span>🏢</span> Private
                </button>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="login-email" className="form-label">
                User ID / Email
              </label>
              <input
                id="login-email"
                type="text"
                className="form-input"
                placeholder="e.g. superadmin_demo or admin_userid"
                value={usernameOrEmail}
                onChange={(e) => { setUsernameOrEmail(e.target.value); setError(''); }}
                autoComplete="username"
                spellCheck={false}
                required
              />
            </div>

            <div className="form-group">
              <div className={styles.passwordLabelRow}>
                <label htmlFor="login-password" className="form-label">Password</label>
                <button
                  type="button"
                  id="link-forgot-password"
                  className={styles.forgotLink}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                  onClick={() => {
                    setError('');
                    setForgotError('');
                    setForgotSuccess('');
                    setForgotStep(1);
                    setForgotIdentifier(usernameOrEmail);
                    setIsForgotMode(true);
                  }}
                >
                  Forgot Password?
                </button>
              </div>
              <div className={styles.passwordWrap}>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(''); }}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className={styles.showPasswordBtn}
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            {error && (
              <div className={styles.errorMsg} role="alert">
                {error}
              </div>
            )}

            <button
              id="login-submit"
              type="submit"
              className={`btn btn-primary ${styles.submitBtn}`}
              disabled={loading}
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        )}

        <div className={styles.backLink} style={{ marginTop: '24px' }}>
          <Link href="/">← Back to GreenNexa website</Link>
        </div>
      </div>

      {/* Right panel — decorative */}
      <div className={styles.loginPanel} aria-hidden="true">
        <div className={styles.panelContent}>
          <h2 className={styles.panelTitle}>AI-Powered Sustainable Facility Intelligence</h2>
          <div className={styles.panelStats}>
            {[
              { icon: '⚡', label: 'Energy Intelligence' },
              { icon: '💧', label: 'Water Intelligence' },
              { icon: '🌡️', label: 'Environmental Monitoring' },
              { icon: '🤖', label: 'AI Anomaly Detection' },
              { icon: '📈', label: 'Forecasting' },
              { icon: '🚨', label: 'Smart Alerts' },
            ].map(({ icon, label }) => (
              <div key={label} className={styles.panelStat}>
                <span>{icon}</span>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
