/**
 * Combined application providers — wraps React Query, Theme, WebSocket, and Toast.
 */

import type { ReactNode } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { QueryProvider } from './QueryProvider';
import { ThemeProvider } from './ThemeProvider';
import { WebSocketProvider } from './WebSocketProvider';
import { SkipLink } from '@/components/atoms/SkipLink';
import { LiveRegion } from '@/components/atoms/LiveRegion';

interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  return (
    <QueryProvider>
      <BrowserRouter>
        <ThemeProvider>
          <WebSocketProvider>
            <SkipLink />
            <LiveRegion />
            {children}
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: 'var(--color-bg-secondary)',
                  color: 'var(--color-text-primary)',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-lg)',
                  fontSize: '0.875rem',
                },
                success: {
                  iconTheme: { primary: '#10b981', secondary: '#fff' },
                },
                error: {
                  iconTheme: { primary: '#ef4444', secondary: '#fff' },
                },
              }}
            />
          </WebSocketProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryProvider>
  );
}

