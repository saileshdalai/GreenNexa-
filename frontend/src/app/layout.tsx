import type { Metadata } from 'next';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider } from '@/context/AuthContext';
import { ToastProvider } from '@/context/ToastContext';
import { DemoProvider } from '@/context/DemoContext';
import { NotificationProvider } from '@/context/NotificationContext';
import { DashboardStyleProvider } from '@/context/DashboardStyleContext';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'GreenNexa — AI-Powered Sustainable Facility Intelligence',
    template: '%s | GreenNexa',
  },
  description:
    'GreenNexa is an AI-powered SaaS platform for intelligent and sustainable management of colleges, hospitals, offices and commercial facilities. Monitor, predict and optimize energy, water, waste and environmental data.',
  keywords: [
    'sustainable facility management',
    'AI facility intelligence',
    'IoT energy monitoring',
    'anomaly detection',
    'sustainability SaaS',
    'GreenNexa',
  ],
  authors: [{ name: 'GreenNexa' }],
  creator: 'GreenNexa',
  metadataBase: new URL('https://greennexa.app'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'GreenNexa',
    title: 'GreenNexa — AI-Powered Sustainable Facility Intelligence',
    description:
      'Monitor. Predict. Optimize. GreenNexa combines AI, IoT and analytics to give facilities actionable sustainability intelligence.',
    images: [{ url: '/branding/greennexa-logo.png' }],
  },
  icons: {
    icon: '/branding/greennexa-logo.png',
    shortcut: '/branding/greennexa-logo.png',
    apple: '/branding/greennexa-logo.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var savedTheme = localStorage.getItem('greennexa_theme');
                  var theme = (savedTheme === 'night' || savedTheme === 'day') ? savedTheme : 'day';
                  document.documentElement.setAttribute('data-theme', theme);
                  document.documentElement.classList.add('theme-' + theme);

                  var savedColor = localStorage.getItem('greennexa_color_theme');
                  if (savedColor && ['emerald', 'ocean-blue', 'indigo', 'teal', 'graphite', 'amber'].indexOf(savedColor) !== -1) {
                    document.documentElement.setAttribute('data-color-theme', savedColor);
                  } else {
                    document.documentElement.setAttribute('data-color-theme', 'emerald');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body>
        <ThemeProvider>
          <AuthProvider>
            <ToastProvider>
              <DemoProvider>
                <NotificationProvider>
                  <DashboardStyleProvider>
                    {children}
                  </DashboardStyleProvider>
                </NotificationProvider>
              </DemoProvider>
            </ToastProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

