'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useRouter, usePathname } from 'next/navigation';
import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useDemo, calculateWeekday, getCurrentModuleFromPath } from '@/context/DemoContext';
import { useTheme } from '@/context/ThemeContext';
import {
  LogOut,
  Building2,
  Bell,
  Tv,
  Calendar,
  ChevronRight,
  ChevronDown,
  MoreHorizontal,
  Sliders,
  CreditCard,
  Mail,
  Shield,
  MapPin,
  PlusCircle,
  Database,
} from 'lucide-react';
import { api } from '@/lib/api';
import { isMunicipality } from '@/lib/organisation';
import { AddWardModal } from '@/components/municipality/AddWardModal';
import { AddGovernmentOrgModal } from '@/components/municipality/AddGovernmentOrgModal';
import { DashboardStyleMenu } from '@/components/dashboard/DashboardStyleMenu';
import { ThemeColorMenu } from '@/components/dashboard/ThemeColorMenu';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { useNotifications } from '@/context/NotificationContext';
import { RedDotIndicator } from '@/components/ui/RedDotIndicator';
import styles from './Header.module.css';

const NAV_LINKS = [
  { href: '/',             label: 'Home' },
  { href: '/about',        label: 'About' },
  { href: '/features',     label: 'Features' },
  { href: '/how-it-works', label: 'How It Works' },
  { href: '/pricing',      label: 'Pricing' },
  { href: '/contact',      label: 'Contact' },
];

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false); // Mobile hamburger menu for public pages
  const [dashboardMenuOpen, setDashboardMenuOpen] = useState(false); // Single "..." menu for logged-in dashboard
  const [scrolled, setScrolled] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);

  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const { user, token, logout, activeOrgId, setActiveOrgId, organisations, currentOrg } = useAuth();
  const { hasUnread } = useNotifications();
  const {
    demoModeActive,
    activeDemoModules,
    toggleDemoMode,
    presentationModeActive,
    togglePresentationMode,
    simulatedDate,
    formattedDate,
    changeSimulatedDay,
    setSimulatedDateDirect,
    refreshSimulatedDay,
    isChangingDay,
    simElapsedSeconds,
  } = useDemo();
  const { toggleTheme, isNight } = useTheme();

  const [dateModalOpen, setDateModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState(simulatedDate || '2026-09-20');
  const [savingDate, setSavingDate] = useState(false);
  const [wardModalOpen, setWardModalOpen] = useState(false);
  const [govOrgModalOpen, setGovOrgModalOpen] = useState(false);
  const [addMenuOpen, setAddMenuOpen] = useState(true);

  const effectiveCurrentOrg = currentOrg || organisations.find((o) => o.id === (activeOrgId || user?.organisation_id));
  const isMunicipalityOrg = effectiveCurrentOrg ? isMunicipality(effectiveCurrentOrg) : false;

  useEffect(() => {
    if (simulatedDate) {
      setSelectedDate(simulatedDate);
    }
  }, [simulatedDate]);

  useEffect(() => {
    if (activeOrgId) {
      refreshSimulatedDay(activeOrgId);
    }
  }, [activeOrgId]);

  useEffect(() => {
    if (!token) return;
    api.get<{ unread_count: number }>('/api/v1/messages/unread-count')
      .then((data) => {
        if (data && typeof data.unread_count === 'number') {
          setUnreadCount(data.unread_count);
        }
      })
      .catch(() => {});
  }, [token]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Close dashboard menu on click outside
  useEffect(() => {
    if (!dashboardMenuOpen) return;
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setDashboardMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [dashboardMenuOpen]);

  // Close dashboard menu on Escape key press
  useEffect(() => {
    if (!dashboardMenuOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDashboardMenuOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [dashboardMenuOpen]);

  // Public mobile menu close on click
  useEffect(() => {
    if (!menuOpen) return;
    const close = () => setMenuOpen(false);
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [menuOpen]);

  // Keyboard navigation within the dashboard menu
  const handleMenuKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!menuRef.current) return;
      const items = Array.from(
        menuRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), a[href]')
      );
      if (items.length === 0) return;
      const currentIndex = items.indexOf(document.activeElement as HTMLElement);
      if (event.key === 'ArrowDown') {
        const nextIndex = (currentIndex + 1) % items.length;
        items[nextIndex]?.focus();
      } else {
        const prevIndex = (currentIndex - 1 + items.length) % items.length;
        items[prevIndex]?.focus();
      }
    }
  };

  const handleLogout = () => {
    setDashboardMenuOpen(false);
    logout();
    router.push('/');
  };

  return (
    <header className={`${styles.header} ${scrolled ? styles.scrolled : ''}`}>
      <div className={`container ${styles.inner}`}>

        {/* Logo */}
        <Link href="/" className={styles.logo} aria-label="GreenNexa home">
          <Image
            src="/branding/greennexa-logo.png"
            alt="GreenNexa — AI-Powered Sustainable Facility Intelligence"
            width={160}
            height={52}
            priority
            style={{ objectFit: 'contain', width: 'auto', height: '44px' }}
          />
        </Link>

        {/* Desktop nav - ONLY visible for public visitors, NOT when logged in */}
        {!user && (
          <nav className={styles.desktopNav} aria-label="Main navigation">
            {NAV_LINKS.map(({ href, label }) => (
              <Link key={href} href={href} className={styles.navLink}>
                {label}
              </Link>
            ))}
          </nav>
        )}

        {/* Header controls & CTAs */}
        <div className={styles.headerControls} style={{ marginLeft: user ? 'auto' : undefined }}>
          {user ? (
            <>
              {/* Super admin org switcher */}
              {user.role === 'SUPER_ADMIN' && organisations.length > 0 && (
                <div className={styles.superAdminSwitcher}>
                  <Building2 size={14} color="var(--clr-primary)" />
                  <select
                    value={activeOrgId || ''}
                    onChange={(e) => setActiveOrgId(e.target.value)}
                    aria-label="Switch organization"
                    className={styles.orgSelect}
                  >
                    {organisations.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name} ({org.id})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Simulated Calendar Date & Day (clickable for manual edit) */}
              <button
                type="button"
                onClick={() => {
                  setSelectedDate(simulatedDate || '2026-09-20');
                  setDateModalOpen(true);
                }}
                title="Click to edit simulated date"
                aria-label="Edit simulation date"
                className={styles.simulatedDatePill}
              >
                <Calendar size={13} />
                <span>{formattedDate || '20 Sep 2026 / SUN'}</span>
              </button>

              {/* 30s Autonomous Simulator Cycle Indicator */}
              {demoModeActive && (
                <div
                  title="30-second autonomous simulation cycle (persistent across routes)"
                  aria-label="Simulation cycle timer"
                  className={styles.cycleIndicator}
                >
                  <span className={styles.cycleDot} />
                  <span className={styles.cycleText}>Cycle: {simElapsedSeconds}s / 30s</span>
                </div>
              )}

              {/* ONE single "..." menu container */}
              <div className={styles.moreMenuContainer} ref={menuRef}>
                <button
                  ref={triggerRef}
                  type="button"
                  id="dashboard-more-menu-btn"
                  className={styles.moreMenuBtn}
                  onClick={(e) => {
                    e.stopPropagation();
                    setDashboardMenuOpen((prev) => !prev);
                  }}
                  aria-expanded={dashboardMenuOpen}
                  aria-haspopup="menu"
                  aria-controls="dashboard-more-menu-dropdown"
                  aria-label="Dashboard options menu"
                  title="Options (⋯)"
                  style={{ position: 'relative' }}
                >
                  <MoreHorizontal size={20} />
                </button>

                {dashboardMenuOpen && (
                  <div
                    id="dashboard-more-menu-dropdown"
                    role="menu"
                    aria-labelledby="dashboard-more-menu-btn"
                    className={styles.dropdownMenu}
                    onKeyDown={handleMenuKeyDown}
                    onWheel={(e) => e.stopPropagation()}
                  >
                    {/* 1. Dashboard Style — presentation only, never affects data */}
                    <DashboardStyleMenu onSelected={() => setDashboardMenuOpen(false)} />

                    {/* 2. Theme / Colour — independent color themes */}
                    <ThemeColorMenu onSelected={() => setDashboardMenuOpen(false)} />

                    {/* 3. Municipality-only: Add -> Ward, Organisation */}
                    {isMunicipalityOrg && (
                      <div style={{ borderBottom: '1px solid var(--clr-border)', paddingBottom: '4px', marginBottom: '4px' }}>
                        <button
                          type="button"
                          role="menuitem"
                          className={styles.menuItem}
                          onClick={(e) => {
                            e.stopPropagation();
                            setAddMenuOpen((prev) => !prev);
                          }}
                          aria-expanded={addMenuOpen}
                          id="header-menu-add"
                          title="Add Ward or Organisation"
                        >
                          <span className={styles.menuItemLeft}>
                            <PlusCircle size={15} style={{ color: 'var(--clr-primary)', flexShrink: 0 }} />
                            <span className={styles.menuItemText}>Add</span>
                          </span>
                          <ChevronDown
                            size={13}
                            style={{
                              transform: addMenuOpen ? 'rotate(180deg)' : 'none',
                              transition: 'transform 0.15s ease',
                              color: 'var(--clr-text-muted)',
                            }}
                          />
                        </button>
                        {addMenuOpen && (
                          <div
                            role="group"
                            aria-label="Add Options"
                            style={{
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '2px',
                              padding: '4px 6px',
                              background: 'var(--clr-surface-2)',
                              borderRadius: '8px',
                              margin: '2px 0 4px 10px',
                              borderLeft: '2px solid var(--clr-primary)',
                            }}
                          >
                            <button
                              type="button"
                              role="menuitem"
                              className={styles.menuItem}
                              onClick={() => {
                                setDashboardMenuOpen(false);
                                setWardModalOpen(true);
                              }}
                              id="header-menu-add-ward"
                              title="Add Ward"
                            >
                              <span className={styles.menuItemLeft}>
                                <MapPin size={15} style={{ color: '#0284c7' }} />
                                <span className={styles.menuItemText}>Ward</span>
                              </span>
                              <ChevronRight size={13} className={styles.chevronIcon} />
                            </button>
                            <button
                              type="button"
                              role="menuitem"
                              className={styles.menuItem}
                              onClick={() => {
                                setDashboardMenuOpen(false);
                                setGovOrgModalOpen(true);
                              }}
                              id="header-menu-add-org"
                              title="Associate Government Organisation"
                            >
                              <span className={styles.menuItemLeft}>
                                <Building2 size={15} style={{ color: 'var(--clr-primary)' }} />
                                <span className={styles.menuItemText}>Organisation</span>
                              </span>
                              <ChevronRight size={13} className={styles.chevronIcon} />
                            </button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Super Admin: Manage Storage (visible ONLY to SUPER_ADMIN) */}
                    {user?.role === 'SUPER_ADMIN' && (
                      <Link
                        href="/super-admin/storage"
                        role="menuitem"
                        className={styles.menuItem}
                        onClick={() => setDashboardMenuOpen(false)}
                        id="header-menu-manage-storage"
                        title="Manage Storage"
                      >
                        <span className={styles.menuItemLeft}>
                          <Database size={15} className={styles.itemIconGreen} />
                          <span className={styles.menuItemText}>Manage Storage</span>
                        </span>
                        <ChevronRight size={13} className={styles.chevronIcon} />
                      </Link>
                    )}

                    {/* 1. Change Day */}
                    <button
                      type="button"
                      role="menuitem"
                      className={styles.menuItem}
                      disabled={isChangingDay}
                      onClick={() => {
                        changeSimulatedDay(1, activeOrgId);
                        setDashboardMenuOpen(false);
                      }}
                      title="Advance calendar by 1 day"
                    >
                      <span className={styles.menuItemLeft}>
                        <Calendar size={15} className={styles.itemIconGreen} />
                        <span className={styles.menuItemText}>
                          {isChangingDay ? 'Advancing...' : 'Change Day'}
                        </span>
                      </span>
                      <ChevronRight size={13} className={styles.chevronIcon} />
                    </button>

                    {/* 2. Demo Mode ON/OFF (Page/Module Scoped) */}
                    <button
                      type="button"
                      role="menuitem"
                      className={styles.menuItem}
                      onClick={() => {
                        const currentMod = getCurrentModuleFromPath(pathname);
                        toggleDemoMode(currentMod || undefined);
                        setDashboardMenuOpen(false);
                      }}
                      title="Toggle Demo Mode"
                    >
                      <span className={styles.menuItemLeft}>
                        <Sliders size={15} className={demoModeActive ? styles.itemIconGreen : styles.itemIconMuted} />
                        <span className={styles.menuItemText}>
                          {(() => {
                            const mod = getCurrentModuleFromPath(pathname);
                            return mod ? `Demo Mode (${mod.charAt(0).toUpperCase() + mod.slice(1)})` : 'Demo Mode ON/OFF';
                          })()}
                        </span>
                      </span>
                      <span className={`${styles.statusPill} ${demoModeActive ? styles.statusPillActive : ''}`}>
                        {demoModeActive ? (activeDemoModules.length > 0 ? `ON (${activeDemoModules[0].toUpperCase()})` : 'ON') : 'OFF'}
                      </span>
                    </button>

                    {/* 4. Notifications */}
                    <Link
                      href="/messages"
                      role="menuitem"
                      className={styles.menuItem}
                      onClick={() => setDashboardMenuOpen(false)}
                      title="Notifications & Messages"
                    >
                      <span className={styles.menuItemLeft}>
                        <Bell size={15} className={(unreadCount > 0 || hasUnread) ? styles.itemIconRed : styles.itemIconMuted} />
                        <span className={styles.menuItemText}>Notifications</span>
                      </span>
                      {(unreadCount > 0 || hasUnread) && (
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <RedDotIndicator size="sm" label="Unread notifications" />
                          {unreadCount > 0 && <span className={styles.unreadPill}>{unreadCount}</span>}
                        </div>
                      )}
                    </Link>

                    {/* 5. ☀ Day Mode / 🌙 Night Mode */}
                    <button
                      type="button"
                      role="menuitem"
                      className={styles.menuItem}
                      onClick={() => {
                        toggleTheme();
                        setDashboardMenuOpen(false);
                      }}
                      title={isNight ? 'Switch to Day Mode' : 'Switch to Night Mode'}
                    >
                      <span className={styles.menuItemLeft}>
                        <span style={{ fontSize: '13px', lineHeight: 1, display: 'inline-flex' }}>
                          {isNight ? '🌙' : '☀️'}
                        </span>
                        <span className={styles.menuItemText}>☀ Day Mode / 🌙 Night Mode</span>
                      </span>
                      <span className={styles.statusPill}>
                        {isNight ? 'Night' : 'Day'}
                      </span>
                    </button>

                    {/* 6. Logout */}
                    <button
                      type="button"
                      role="menuitem"
                      className={styles.menuItem}
                      onClick={handleLogout}
                      title="Logout"
                    >
                      <span className={styles.menuItemLeft}>
                        <LogOut size={15} className={styles.itemIconRed} />
                        <span className={styles.menuItemText}>Logout</span>
                      </span>
                    </button>

                    {/* 7. Pricing */}
                    <Link
                      href="/pricing"
                      role="menuitem"
                      className={styles.menuItem}
                      onClick={() => setDashboardMenuOpen(false)}
                      title="Pricing Plans"
                    >
                      <span className={styles.menuItemLeft}>
                        <CreditCard size={15} className={styles.itemIconMuted} />
                        <span className={styles.menuItemText}>Pricing</span>
                      </span>
                    </Link>

                    {/* 8. Contact Us */}
                    <Link
                      href="/contact"
                      role="menuitem"
                      className={styles.menuItem}
                      onClick={() => setDashboardMenuOpen(false)}
                      title="Contact Us"
                    >
                      <span className={styles.menuItemLeft}>
                        <Mail size={15} className={styles.itemIconMuted} />
                        <span className={styles.menuItemText}>Contact Us</span>
                      </span>
                    </Link>

                    {/* 9. Privacy Policy */}
                    <Link
                      href="/privacy"
                      role="menuitem"
                      className={styles.menuItem}
                      onClick={() => setDashboardMenuOpen(false)}
                      title="Privacy Policy"
                    >
                      <span className={styles.menuItemLeft}>
                        <Shield size={15} className={styles.itemIconMuted} />
                        <span className={styles.menuItemText}>Privacy Policy</span>
                      </span>
                    </Link>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <Link href="/login" className="btn btn-primary btn-sm">
                Login
              </Link>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <ThemeToggle />
              </div>
              <button
                id="mobile-menu-toggle"
                className={styles.hamburger}
                aria-label="Toggle mobile menu"
                aria-expanded={menuOpen}
                onClick={(e) => { e.stopPropagation(); setMenuOpen((v) => !v); }}
              >
                <span className={`${styles.bar} ${menuOpen ? styles.barOpen1 : ''}`} />
                <span className={`${styles.bar} ${menuOpen ? styles.barOpen2 : ''}`} />
                <span className={`${styles.bar} ${menuOpen ? styles.barOpen3 : ''}`} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Public Mobile menu - ONLY for unauthenticated visitors */}
      {!user && menuOpen && (
        <div className={styles.mobileMenu} onClick={(e) => e.stopPropagation()}>
          <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--clr-border)', marginBottom: '8px', display: 'flex', justifyContent: 'center' }}>
            <ThemeToggle />
          </div>
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={styles.mobileLink}
              onClick={() => setMenuOpen(false)}
            >
              {label}
            </Link>
          ))}
          <Link
            href="/login"
            className={`btn btn-primary ${styles.mobileLoginBtn}`}
            onClick={() => setMenuOpen(false)}
          >
            Login
          </Link>
        </div>
      )}

      {/* Edit Simulation Date Modal */}
      {dateModalOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.75)',
            backdropFilter: 'blur(4px)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
          onClick={() => setDateModalOpen(false)}
        >
          <div
            style={{
              backgroundColor: 'var(--clr-surface-2, #1e293b)',
              borderRadius: '16px',
              border: '1px solid var(--clr-border, rgba(255, 255, 255, 0.15))',
              maxWidth: '420px',
              width: '100%',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)',
              color: 'var(--clr-text-primary, #f8fafc)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: 700 }}>
              Edit Simulation Date
            </h3>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--clr-text-secondary)', marginBottom: '6px' }}>
                Date:
              </label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--clr-border, #334155)',
                  backgroundColor: 'var(--clr-surface-1, #0f172a)',
                  color: 'var(--clr-text-primary, #f8fafc)',
                  fontSize: '14px',
                }}
              />
            </div>
            <div style={{ marginBottom: '24px', fontSize: '14px', color: 'var(--clr-text-secondary)' }}>
              Day: <strong style={{ color: 'var(--clr-primary, #10b981)' }}>{calculateWeekday(selectedDate)} (automatic)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => setDateModalOpen(false)}
                disabled={savingDate}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={savingDate || !selectedDate}
                onClick={async () => {
                  setSavingDate(true);
                  try {
                    await setSimulatedDateDirect(selectedDate, activeOrgId);
                    setDateModalOpen(false);
                  } catch {
                    // Handled in setSimulatedDateDirect
                  } finally {
                    setSavingDate(false);
                  }
                }}
              >
                {savingDate ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {currentOrg && isMunicipality(currentOrg) && (
        <>
          <AddWardModal
            municipalityId={currentOrg.id}
            municipalityName={currentOrg.name}
            isOpen={wardModalOpen}
            onClose={() => setWardModalOpen(false)}
          />
          <AddGovernmentOrgModal
            municipalityId={currentOrg.id}
            municipalityName={currentOrg.name}
            isOpen={govOrgModalOpen}
            onClose={() => setGovOrgModalOpen(false)}
          />
        </>
      )}
    </header>
  );
}
